from sqlalchemy import text, select, column, func, desc, or_, cast
from sqlalchemy import sql
from sqlalchemy.sql import sqltypes
from sqlalchemy.exc import SQLAlchemyError

from jet_bridge_base import fields
from jet_bridge_base.db import create_session
from jet_bridge_base.exceptions.sql import SqlError
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.fields.sql_params import SqlParamsSerializers
from jet_bridge_base.filters import lookups
from jet_bridge_base.filters.filter import EMPTY_VALUES
from jet_bridge_base.filters.model_group import get_query_func_by_name
from jet_bridge_base.filters.filter_for_dbfield import filter_for_data_type
from jet_bridge_base.serializers.serializer import Serializer
from jet_bridge_base.utils.db_types import map_query_type


class ColumnSerializer(Serializer):
    name = fields.CharField()
    data_type = fields.CharField()


class FilterItemSerializer(Serializer):
    name = fields.CharField()
    value = fields.CharField(required=False)


class AggregateSerializer(Serializer):
    func = fields.CharField()
    column = fields.CharField(required=False)


class GroupSerializer(Serializer):
    xColumn = fields.CharField()
    xLookup = fields.CharField(required=False)
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
    timezone = fields.CharField(required=False)
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

        return attrs

    def aggregate_queryset(self, subquery, data):
        func_param = data['aggregate'].get('func').lower()
        column_param = data['aggregate'].get('column')

        y_column = column(column_param) if column_param is not None else None
        y_func = get_query_func_by_name(func_param, y_column)

        if y_func is None:
            return subquery.filter(sql.false())
        else:
            return select([y_func]).select_from(subquery)

    def group_queryset(self, subquery, data):
        y_func_param = data['group'].get('yFunc').lower()
        x_lookup_param = data['group'].get('xLookup')
        x_column_param = data['group'].get('xColumn')
        y_column_param = data['group'].get('yColumn')

        x_column = column(x_column_param) if x_column_param is not None else None
        y_column = column(y_column_param) if y_column_param is not None else None
        y_func = get_query_func_by_name(y_func_param, y_column)

        if x_lookup_param and x_lookup_param in ['date']:
            x_lookup = getattr(func, x_lookup_param)(x_column)
        else:
            x_lookup = x_column

        if y_func is None:
            return subquery.filter(sql.false())
        else:
            queryset = select([x_lookup.label('group'), y_func.label('y_func')]).select_from(subquery)
            return queryset.group_by('group').order_by('group')

    def filter_queryset(self, queryset, data):
        filters_instances = []

        for item in data.get('columns', []):
            query_type = map_query_type(item['data_type'])()
            filter_data = filter_for_data_type(query_type)
            for lookup in filter_data['lookups']:
                instance = filter_data['filter_class'](
                    name=item['name'],
                    column=column(item['name']),
                    lookup=lookup
                )
                filters_instances.append(instance)

        def get_filter_value(name):
            filter_items = list(filter(lambda x: x['name'] == name, data.get('filters', [])))
            return filter_items[0]['value'] if len(filter_items) else None

        for item in filters_instances:
            if item.name:
                argument_name = '{}__{}'.format(item.name, item.lookup)
                value = get_filter_value(argument_name)

                if value is None and item.lookup == lookups.DEFAULT_LOOKUP:
                    value = get_filter_value(item.name)
            else:
                value = None

            queryset = item.filter(queryset, value)

        search = get_filter_value('_search')

        if search not in EMPTY_VALUES:
            def map_column(item):
                field = column(item['name'])
                query_type = map_query_type(item['data_type'])()

                if isinstance(query_type, (sqltypes.Integer, sqltypes.Numeric)):
                    return cast(field, sqltypes.String).__eq__(search)
                elif isinstance(query_type, sqltypes.String):
                    return field.ilike('%{}%'.format(search))
                elif isinstance(query_type, sqltypes.JSON):
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

    def map_order_field(self, name):
        descending = False
        if name.startswith('-'):
            name = name[1:]
            descending = True
        field = column(name)
        if descending:
            field = desc(field)
        return field

    def sort_queryset(self, queryset, data):
        if 'order_by' in data:
            order_by = list(map(lambda x: self.map_order_field(x), data['order_by']))
            queryset = queryset.order_by(*order_by)

        return queryset

    def execute(self, data):
        request = self.context.get('request')
        session = create_session(request)

        query = data['query']

        if data['v'] >= 2:
            params = data.get('params_obj', {})
        else:
            params = data.get('params', [])

        if 'timezone' in data:
            try:
                session.execute('SET TIME ZONE :tz', {'tz': data['timezone']})
            except SQLAlchemyError:
                session.rollback()
                pass

        subquery = text(query).columns().subquery('__jet_q2')
        count_rows = None

        if data['count']:
            try:
                count_queryset = select([func.count()]).select_from(subquery)
                count_queryset = self.filter_queryset(count_queryset, data)

                count_result = session.execute(count_queryset, params)
                count_rows = count_result.all()[0][0]
            except Exception:
                pass

        try:
            if 'aggregate' in data:
                queryset = self.aggregate_queryset(subquery, data)
            elif 'group' in data:
                queryset = self.group_queryset(subquery, data)
            else:
                queryset = select(['*']).select_from(subquery)

            queryset = self.filter_queryset(queryset, data)

            if 'aggregate' not in data and 'group' not in data:
                queryset = self.paginate_queryset(queryset, data)

            if 'group' not in data:
                queryset = self.sort_queryset(queryset, data)

            result = session.execute(queryset, params)

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
                else:
                    return x

            def map_row(row):
                return list(map(lambda x: map_row_column(row[x]), row.keys()))

            response = {'data': list(map(map_row, result)), 'columns': list(map(map_column, result.keys()))}

            if count_rows is not None:
                response['count'] = count_rows

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
