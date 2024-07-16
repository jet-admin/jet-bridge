import datetime
import time

from jet_bridge_base.fields.datetime import datetime_apply_default_timezone
from sqlalchemy import text, select, column, func, desc, or_, cast
from sqlalchemy import sql
from sqlalchemy.sql import sqltypes, quoted_name
from sqlalchemy.exc import SQLAlchemyError

from jet_bridge_base import fields
from jet_bridge_base.db import create_session, get_type_code_to_sql_type
from jet_bridge_base.exceptions.sql import SqlError
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.fields.sql_params import SqlParamsSerializers
from jet_bridge_base.filters import lookups
from jet_bridge_base.filters.filter import EMPTY_VALUES, safe_array
from jet_bridge_base.filters.model_group import get_query_func_by_name, get_query_lookup_func_by_name
from jet_bridge_base.filters.filter_for_dbfield import filter_for_data_type
from jet_bridge_base.serializers.model_serializer import get_column_data_type
from jet_bridge_base.serializers.serializer import Serializer
from jet_bridge_base.utils.db_types import map_to_sql_type, sql_to_map_type
from jet_bridge_base.utils.queryset import get_session_engine, apply_session_timezone


class ColumnSerializer(Serializer):
    name = fields.CharField()
    data_type = fields.CharField()


class FilterItemSerializer(Serializer):
    name = fields.CharField()
    value = fields.RawField(allow_many=True, required=False)


class AggregateSerializer(Serializer):
    func = fields.CharField()
    column = fields.CharField(required=False)


class GroupSerializer(Serializer):
    xColumn = fields.CharField()
    xLookup = fields.CharField(required=False)
    yColumn = fields.CharField(required=False)
    yFunc = fields.CharField()


class GroupsItemSerializer(Serializer):
    xColumn = fields.CharField()
    xLookup = fields.CharField(required=False)


class GroupsSerializer(Serializer):
    xColumns = GroupsItemSerializer(many=True)
    yColumn = fields.CharField(required=False)
    yFunc = fields.CharField()


class SqlSerializer(Serializer):
    query = fields.CharField()
    offset = fields.IntegerField(required=False)
    limit = fields.IntegerField(required=False)
    order_by = fields.CharField(many=True, required=False)
    count = fields.BooleanField(default=False)
    columns = ColumnSerializer(many=True, required=False)
    filters = FilterItemSerializer(many=True, required=False)
    aggregate = AggregateSerializer(required=False)
    group = GroupSerializer(required=False)
    groups = GroupsSerializer(required=False)
    timezone = fields.CharField(required=False)
    schema = fields.CharField(required=False)
    params = SqlParamsSerializers(required=False)
    params_obj = fields.JSONField(required=False)
    v = fields.IntegerField(default=1)

    def validate(self, attrs):
        forbidden = ['insert', 'update', 'delete', 'grant', 'show']
        for i in range(len(forbidden)):
            forbidden.append('({}'.format(forbidden[i]))
        if any(map(lambda x: ' {} '.format(attrs['query'].lower()).find(' {} '.format(x)) != -1, forbidden)):
            raise ValidationError({'query': 'forbidden query'})

        if attrs['v'] < 2:
            i = 0
            while attrs['query'].find('%s') != -1:
                attrs['query'] = attrs['query'].replace('%s', ':param_{}'.format(i), 1)
                i += 1

        if 'limit' in attrs:
            if attrs['limit'] > 1000:
                attrs['limit'] = 1000
            elif attrs['limit'] < 0:
                del attrs['limit']

        return attrs

    def aggregate_queryset(self, subquery, data, session):
        func_param = data['aggregate'].get('func').lower()
        column_param = data['aggregate'].get('column')

        y_column = self.get_column(session, column_param) if column_param is not None else None
        y_func = get_query_func_by_name(func_param, y_column)

        if y_func is None:
            return subquery.filter(sql.false())
        else:
            return select([y_func]).select_from(subquery)

    def group_queryset(self, subquery, data, session):
        def get_y_func(group):
            y_func_param = group.get('yFunc').lower()
            y_column_param = group.get('yColumn')
            y_column = self.get_column(session, y_column_param) if y_column_param is not None else None
            return get_query_func_by_name(y_func_param, y_column)

        if 'groups' in data:
            y_func = get_y_func(data['groups'])
        elif 'group' in data:
            y_func = get_y_func(data['group'])
        else:
            y_func = None

        if y_func is None:
            return subquery.filter(sql.false())

        def group_name(i):
            if i == 0 and get_session_engine(session) != 'mssql':
                return 'group'
            else:
                return 'group_{}'.format(i + 1)

        def map_group_column(group, i):
            x_lookup_param = group.get('xLookup')
            x_column_param = group.get('xColumn')
            x_column = self.get_column(session, x_column_param) if x_column_param is not None else None

            lookup_params = x_lookup_param.split('_') if x_lookup_param else []
            lookup_type = lookup_params[0] if len(lookup_params) >= 1 else None
            lookup_param = lookup_params[1] if len(lookup_params) >= 2 else None

            return get_query_lookup_func_by_name(session, lookup_type, lookup_param, x_column).label(group_name(i))

        if 'groups' in data:
            x_lookups = list(map(lambda x: map_group_column(x[1], x[0]), enumerate(data['groups']['xColumns'])))
        elif 'group' in data:
            x_lookups = [map_group_column(data['group'], 0)]

        x_lookup_names = list(map(lambda x: x.name, x_lookups))

        queryset = select([*x_lookups, y_func.label('y_func')]).select_from(subquery)

        if get_session_engine(session) == 'mssql':
            return queryset.group_by(*x_lookups).order_by(*x_lookup_names)
        else:
            return queryset.group_by(*x_lookup_names).order_by(*x_lookup_names)

    def filter_queryset(self, queryset, data):
        filters_instances = []
        request = self.context.get('request')
        session = request.session

        for item in data.get('columns', []):
            query_type = map_to_sql_type(item['data_type'])()
            filter_data = filter_for_data_type(query_type)
            for lookup in filter_data['lookups']:
                for exclude in [False, True]:
                    column_ = self.get_column(session, item['name'], type_=query_type)
                    instance = filter_data['filter_class'](
                        name=item['name'],
                        column=column_,
                        lookup=lookup,
                        exclude=exclude
                    )
                    filters_instances.append(instance)

        def get_filter_value(name, filters_instance=None):
            filter_items = list(filter(lambda x: x['name'] == name, data.get('filters', [])))

            if not len(filter_items):
                return

            return filter_items[0]['value']

        for item in filters_instances:
            if item.name:
                argument_name = '{}__{}'.format(item.name, item.lookup)
                if item.exclude:
                    argument_name = 'exclude__{}'.format(argument_name)
                value = get_filter_value(argument_name, item)

                if value is None and item.lookup == lookups.DEFAULT_LOOKUP:
                    argument_name = item.name
                    if item.exclude:
                        argument_name = 'exclude__{}'.format(argument_name)
                    value = get_filter_value(argument_name, item)
            else:
                value = None

            queryset = item.filter(queryset, value)

        search = get_filter_value('_search')

        if search not in EMPTY_VALUES:
            def map_column(item):
                field = self.get_column(session, item['name'])
                query_type = map_to_sql_type(item['data_type'])()

                if isinstance(query_type, (sqltypes.Integer, sqltypes.Numeric)):
                    return cast(field, sqltypes.String).__eq__(search)
                elif isinstance(query_type, (sqltypes.JSON, sqltypes.ARRAY, sqltypes.Enum)):
                    return cast(field, sqltypes.String).ilike('%{}%'.format(search))
                elif isinstance(query_type, sqltypes.String):
                    return cast(field, sqltypes.String).ilike('%{}%'.format(search))

            operators = list(filter(lambda x: x is not None, map(map_column, data.get('columns', []))))
            queryset = queryset.filter(or_(*operators))

        return queryset

    def paginate_queryset(self, queryset, data):
        if 'offset' in data:
            queryset = queryset.offset(data['offset'])

        if 'limit' in data:
            if data['limit']:
                queryset = queryset.limit(data['limit'])
        elif data['v'] >= 2:
            queryset = queryset.limit(100)

        return queryset

    def map_order_field(self, session, name):
        descending = False
        if name.startswith('-'):
            name = name[1:]
            descending = True
        field = self.get_column(session, name)
        if descending:
            field = desc(field)
        return field

    def get_column(self, session, name, **kwargs):
        if get_session_engine(session) == 'oracle':
            name = quoted_name(name, True)
        return column(name, **kwargs)

    def sort_queryset(self, queryset, data, session):
        if 'order_by' in data:
            order_by = list(map(lambda x: self.map_order_field(session, x), data['order_by']))
            queryset = queryset.order_by(*order_by)
        else:
            if 'aggregate' not in data and 'group' not in data and 'groups' not in data:
                if get_session_engine(session) == 'mssql':
                    for item in data.get('columns', []):
                        field = self.get_column(session, item['name'])
                        queryset = queryset.order_by(field)
                        break

        return queryset

    def execute(self, data):
        request = self.context.get('request')
        session = request.session

        query = data['query']

        if data['v'] >= 2:
            params = data.get('params_obj', {})
        else:
            params = data.get('params', [])

        if data.get('timezone') is not None:
            try:
                apply_session_timezone(session, data['timezone'])
            except SQLAlchemyError:
                session.rollback()
                pass

        if 'schema' in data:
            try:
                session.execute('SET search_path TO :schema', {'schema': data['schema']})
            except SQLAlchemyError:
                session.rollback()
                pass

        subquery = text(query).columns().subquery('__jet_q2')
        count_rows = None
        count_query_time = None

        if data['count']:
            try:
                count_queryset = select([func.count()]).select_from(subquery)
                count_queryset = self.filter_queryset(count_queryset, data)

                count_query_start = time.time()
                count_result = session.execute(count_queryset, params)
                count_rows = count_result.all()[0][0]
                count_query_end = time.time()

                count_query_time = round(count_query_end - count_query_start, 3)
            except SQLAlchemyError:
                session.rollback()
            except Exception:
                pass

        try:
            if 'aggregate' in data:
                queryset = self.aggregate_queryset(subquery, data, session)
            elif 'groups' in data or 'group' in data:
                queryset = self.group_queryset(subquery, data, session)
            else:
                queryset = select(['*']).select_from(subquery)

            queryset = self.filter_queryset(queryset, data)

            if 'aggregate' not in data and 'group' not in data and 'groups' not in data:
                queryset = self.paginate_queryset(queryset, data)

            if 'group' not in data and 'groups' not in data:
                queryset = self.sort_queryset(queryset, data, session)

            data_query_start = time.time()
            result = session.execute(queryset, params)
            data_query_end = time.time()

            data_query_time = round(data_query_end - data_query_start, 3)

            def map_column(x):
                if x == '?column?':
                    return
                return x

            def map_row_column(x):
                if isinstance(x, bytes):
                    try:
                        return x.decode('utf-8')
                    except UnicodeDecodeError:
                        return x.hex()
                elif isinstance(x, datetime.datetime):
                    x = datetime_apply_default_timezone(x, request)
                    return x
                else:
                    return x

            def map_row(row):
                return list(map(lambda x: map_row_column(row[x]), row.keys()))

            column_names = result.keys()

            if 'groups' in data or 'group' in data:
                column_names = list(map(lambda x: 'group' if x == 'group_1' else x, column_names))

            cursor_description = result.cursor.description
            response = {
                'data': list(map(map_row, result)),
                'columns': list(map(map_column, column_names))
            }

            type_code_to_sql_type = get_type_code_to_sql_type(request)
            if type_code_to_sql_type:
                def map_column_description(column):
                    name = column.name if hasattr(column, 'name') else ''
                    sql_type = type_code_to_sql_type.get(column.type_code) if hasattr(column, 'type_code') else None
                    return name, {
                        'field': sql_to_map_type(sql_type) if sql_type else None
                    }

                response['column_descriptions'] = dict(map(map_column_description, cursor_description))

            if count_rows is not None:
                response['count'] = count_rows

            limit = queryset._limit
            if limit:
                response['limit'] = limit

            response['data_query_time'] = data_query_time

            if count_rows is not None:
                response['count_query_time'] = count_query_time

            return response
        except SQLAlchemyError as e:
            session.rollback()
            raise SqlError(e)
        except TypeError as e:
            raise SqlError(e)
        except Exception as e:
            raise SqlError(e)
        finally:
            session.close()


class SqlsSerializer(Serializer):
    queries = SqlSerializer(many=True)

    def execute(self, data):
        serializer = SqlSerializer(context=self.context)

        def map_query(query):
            try:
                return serializer.execute(query)
            except SqlError as e:
                return {'error': str(e.detail)}

        return list(map(map_query, data['queries']))
