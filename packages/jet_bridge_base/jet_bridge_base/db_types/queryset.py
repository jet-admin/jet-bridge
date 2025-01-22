import pymongo
import sqlalchemy
from sqlalchemy import desc, sql, func, or_, cast
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeMeta
from sqlalchemy.sql import operators, sqltypes, text
from sqlalchemy.sql.elements import AnnotatedColumnElement, UnaryExpression
from bson import ObjectId

from jet_bridge_base.db_types.mongo import MongoOperator
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.models import data_types
from jet_bridge_base.utils.classes import is_instance_or_subclass

from .common import inspect_uniform, get_session_engine
from .mongo import MongoDeclarativeMeta, MongoColumn, MongoDesc, MongoQueryset


def desc_uniform(column):
    if isinstance(column, MongoColumn):
        return MongoDesc(column)
    else:
        return desc(column)


def empty_filter(cls):
    if isinstance(cls, DeclarativeMeta):
        return sql.false()
    elif isinstance(cls, MongoDeclarativeMeta):
        return cls._id.exists(False)


def get_queryset_order_by(queryset):
    if isinstance(queryset, MongoQueryset):
        return queryset.get_order_by()
    else:
        if hasattr(queryset, '_order_by_clauses') and queryset._order_by_clauses:
            return queryset._order_by_clauses
        elif hasattr(queryset, '_order_by') and queryset._order_by:
            return queryset._order_by
        else:
            return []


def get_queryset_limit(queryset):
    if isinstance(queryset, MongoQueryset):
        return queryset.get_limit()
    else:
        if hasattr(queryset, '_limit_clause') and queryset._limit_clause:
            return queryset._limit_clause
        elif hasattr(queryset, '_limit') and queryset._limit:
            return queryset._limit


def apply_default_ordering(Model, queryset):
    mapper = inspect_uniform(Model)
    pk = mapper.primary_key[0]
    ordering = get_queryset_order_by(queryset)

    def is_pk(x):
        if isinstance(queryset, MongoQueryset):
            return x[0] == pk.name
        else:
            if isinstance(x, AnnotatedColumnElement):
                return x.name == pk.name
            elif isinstance(x, UnaryExpression):
                return hasattr(x.element, 'name') and x.element.name == pk.name and x.modifier == operators.desc_op
        return False

    if ordering is None or not any(map(is_pk, ordering)):
        queryset = queryset.order_by(desc_uniform(pk))

    return queryset


def queryset_count_optimized_for_postgresql(session, db_table):
    try:
        cursor = session.execute(text('SELECT reltuples FROM pg_class WHERE relname = :db_table'), {'db_table': db_table})
        row = cursor.fetchone()
        return int(row[0])
    except SQLAlchemyError:
        session.rollback()
        raise


def queryset_count_optimized_for_mysql(session, db_table):
    try:
        cursor = session.execute(text('EXPLAIN SELECT COUNT(*) FROM `{}`'.format(db_table)))
        row = cursor.fetchone()
        return int(row[8])
    except SQLAlchemyError:
        session.rollback()
        raise


def queryset_count_optimized(session, queryset):
    queryset = queryset.order_by(None)

    if queryset.whereclause is None:
        count_optimized = None

        if isinstance(queryset, MongoQueryset):
            count_optimized = queryset.estimated_document_count()
        else:
            try:
                table = queryset.statement.froms[0].name

                if get_session_engine(queryset.session) == 'postgresql':
                    count_optimized = queryset_count_optimized_for_postgresql(session, table)
                elif get_session_engine(queryset.session) == 'mysql':
                    count_optimized = queryset_count_optimized_for_mysql(session, table)
            except:
                pass

        if count_optimized is not None and count_optimized >= 10000:
            return count_optimized

    try:
        return queryset.count()
    except SQLAlchemyError:
        queryset.session.rollback()
        raise


def get_sql_aggregate_func_by_name(name, column):
    if name == 'count':
        return func.count(column)
    elif name == 'sum':
        return func.sum(column)
    elif name == 'min':
        return func.min(column)
    elif name == 'max':
        return func.max(column)
    elif name == 'avg':
        return func.avg(column)


def get_mongo_aggregate_func_by_name(name, column):
    if name == 'count':
        return {'$count': {}}
    elif name == 'sum':
        return {'$sum': '${}'.format(column.name)}
    elif name == 'min':
        return {'$min': '${}'.format(column.name)}
    elif name == 'max':
        return {'$max': '${}'.format(column.name)}
    elif name == 'avg':
        return {'$avg': '${}'.format(column.name)}


def queryset_aggregate(Model, qs, value):
    if isinstance(qs, MongoQueryset):
        y_column = getattr(Model, value['y_column'])
        y_func = get_mongo_aggregate_func_by_name(value['y_func'], y_column)

        if y_func is None:
            return qs.filter(empty_filter(Model))

        result = qs.aggregate({
            '$group': {
                '_id': None,
                'aggregation': y_func
            }
        })

        return result['aggregation']
    else:
        y_column = getattr(Model, value['y_column'])
        y_func = get_sql_aggregate_func_by_name(value['y_func'], y_column)

        if y_func is None:
            return qs.filter(empty_filter(Model))

        whereclause = qs.whereclause
        qs = qs.session.query(y_func)

        if whereclause is not None:
            qs = qs.filter(whereclause)

        return qs.first()[0]

date_trunc_options = {
    'microsecond': 'microseconds',
    'millisecond': 'milliseconds',
    'second': 'minute',
    'minute': 'minute',
    'hour': 'hour',
    'day': 'day',
    'week': 'week',
    'month': 'month',
    'quarter': 'quarter',
    'year': 'year'
}

strftime_options = {
    'microseconds': '%Y-%m-%d %H:%i:%s.%f',
    # 'milliseconds': '%Y-%m-%d %H:%i:%s.%f',
    'second': '%Y-%m-%d %H:%i:%s',
    'minute': '%Y-%m-%d %H:%i:00',
    'hour': '%Y-%m-%d %H:00:00',
    'day': '%Y-%m-%d',
    # 'week': '%Y-%m-%d',
    'month': '%Y-%m-01',
    # 'quarter': '%Y-%m-%d',
    'year': '%Y-01-01'
}

isoformat_options = {
    'microseconds': '%Y-%m-%dT%H:%M:%S.%LZ',
    # 'milliseconds': '%Y-%m-%d %H:%i:%s.%f',
    'second': '%Y-%m-%dT%H:%M:%S.000Z',
    'minute': '%Y-%m-%dT%H:%M:00.000Z',
    'hour': '%Y-%m-%dT%H:00:00.000Z',
    'day': '%Y-%m-%dT00:00:00.000Z',
    # 'week': '%Y-%m-%d',
    'month': '%Y-%m-01T00:00:00.000Z',
    # 'quarter': '%Y-%m-%d',
    'year': '%Y-01-01T00:00:00.000Z',
}

dateadd_options = {
    'millisecond': 'millisecond',
    'second': 'minute',
    'minute': 'minute',
    'hour': 'hour',
    'day': 'day',
    'week': 'week',
    'month': 'month',
    'quarter': 'quarter',
    'year': 'year'
}


def date_trunc_column_clickhouse(column, date_group):
    if date_group == 'microsecond':
        return func.toStartOfMicrosecond(column)
    elif date_group == 'millisecond':
        return func.toStartOfMillisecond(column)
    elif date_group == 'second':
        return func.toStartOfSecond(column)
    elif date_group == 'minute':
        return func.toStartOfMinute(column)
    elif date_group == 'hour':
        return func.toStartOfHour(column)
    elif date_group == 'day':
        return func.toStartOfDay(column)
    elif date_group == 'week':
        return func.toStartOfWeek(column)
    elif date_group == 'month':
        return func.toStartOfMonth(column)
    elif date_group == 'quarter':
        return func.toStartOfQuarter(column)
    elif date_group == 'year':
        return func.toStartOfYear(column)


def get_sql_group_func_lookup(session, lookup_type, lookup_param, column):
    if lookup_type == 'auto':
        field_type = column.property.columns[0].type if hasattr(column, 'property') else column.type

        if is_instance_or_subclass(field_type, (sqltypes.DateTime, sqltypes.Date)):
            lookup_type = 'date'
            lookup_param = 'day'

    try:
        if lookup_type == 'date':
            date_group = lookup_param or 'day'

            if get_session_engine(session) == 'postgresql':
                if date_group in date_trunc_options:
                    return func.date_trunc(date_trunc_options[date_group], column)
            elif get_session_engine(session) == 'mysql':
                if date_group in strftime_options:
                    return func.date_format(column, strftime_options[date_group])
            elif get_session_engine(session) == 'mssql':
                if date_group in dateadd_options:
                    interval = dateadd_options[date_group]
                    return func.dateadd(text(interval), func.datediff(text(interval), text('0'), column), text('0'))
            elif get_session_engine(session) == 'clickhouse':
                date_trunc = date_trunc_column_clickhouse(column, date_group)
                if date_trunc is not None:
                    return date_trunc
            else:
                if date_group in strftime_options:
                    return func.strftime(strftime_options[date_group], column)
        elif lookup_type == 'plain' or lookup_type == 'auto':
            return column
    except IndexError:
        pass

    if lookup_type:
        print('Unsupported lookup: {}'.format(lookup_type))

    return column


def get_mongo_group_func_lookup(lookup_type, lookup_param, column):
    if lookup_type == 'auto':
        if any(map(lambda x: column.type == x, (data_types.DATE, data_types.DATE_TIME))):
            lookup_type = 'date'
            lookup_param = 'day'

    try:
        if lookup_type == 'date':
            date_group = lookup_param or 'day'

            if date_group in isoformat_options:
                return {'$dateToString': {'format': isoformat_options[date_group], 'date': '${}'.format(column.name)}}
        elif lookup_type == 'plain' or lookup_type == 'auto':
            return '${}'.format(column.name)
    except IndexError:
        pass

    if lookup_type:
        print('Unsupported lookup: {}'.format(lookup_type))

    return '${}'.format(column.name)


def queryset_group(Model, qs, value):
    if isinstance(qs, MongoQueryset):
        x_columns = list(map(lambda x: getattr(Model, x), value['x_columns']))
        y_column = getattr(Model, value['y_column'])
        y_func = get_mongo_aggregate_func_by_name(value['y_func'], y_column)

        if y_func is None:
            return qs.filter(empty_filter(Model))

        def group_name(i):
            if i == 0:
                return 'group'
            else:
                return 'group_{}'.format(i + 1)

        def map_lookup(column, i):
            lookup_name = value['x_lookups'][i] if i < len(value['x_lookups']) else None
            lookup_params = lookup_name.split('_') if lookup_name else []
            lookup_type = lookup_params[0] if len(lookup_params) >= 1 else None
            lookup_param = lookup_params[1] if len(lookup_params) >= 2 else None

            if lookup_type == 'date':
                mapper = inspect_uniform(Model)
                column = mapper.columns.get(column.name)
                if column is not None and not any(
                        map(lambda x: column.type == x, (data_types.DATE, data_types.DATE_TIME))):
                    raise ValidationError('Can\'t apply date functions to non-date field: {}'.format(column.name))

            lookup = get_mongo_group_func_lookup(lookup_type, lookup_param, column)

            return {
                'name': group_name(i),
                'lookup': lookup
            }

        x_lookups = list(map(lambda x: map_lookup(x[1], x[0]), enumerate(x_columns)))

        result = qs.group({
            '$group': {
                '_id': dict(map(lambda x: (x['name'], x['lookup']), x_lookups)),
                'aggregation': y_func
            }
        }, {
            '$sort': dict(map(lambda x: (
                '_id.{}'.format(group_name(x[0])),
                pymongo.ASCENDING
            ), enumerate(x_columns)))
        })

        result = list(map(lambda x: {**x['_id'], 'y_func': x['aggregation']}, result))
        return result
    else:
        x_columns = list(map(lambda x: getattr(Model, x), value['x_columns']))
        y_column = getattr(Model, value['y_column'])
        y_func = get_sql_aggregate_func_by_name(value['y_func'], y_column)

        if y_func is None:
            return qs.filter(empty_filter(Model))

        def group_name(i):
            if i == 0 and get_session_engine(qs.session) != 'mssql':
                return 'group'
            else:
                return 'group_{}'.format(i + 1)

        def map_lookup(column, i):
            lookup_name = value['x_lookups'][i] if i < len(value['x_lookups']) else None
            lookup_params = lookup_name.split('_') if lookup_name else []
            lookup_type = lookup_params[0] if len(lookup_params) >= 1 else None
            lookup_param = lookup_params[1] if len(lookup_params) >= 2 else None

            if lookup_type == 'date':
                mapper = inspect_uniform(Model)
                column = mapper.columns.get(column.name)
                if column is not None and not isinstance(column.type, (sqltypes.DateTime, sqltypes.Date)):
                    raise ValidationError('Can\'t apply date functions to non-date field: {}'.format(column.name))

            lookup = get_sql_group_func_lookup(qs.session, lookup_type, lookup_param, column)
            return lookup.label(group_name(i))

        x_lookups = list(map(lambda x: map_lookup(x[1], x[0]), enumerate(x_columns)))
        x_lookup_names = list(map(lambda x: x.name, x_lookups))

        whereclause = qs.whereclause
        qs = qs.session.query(*x_lookups, y_func.label('y_func'))

        if whereclause is not None:
            qs = qs.filter(whereclause)

        if get_session_engine(qs.session) == 'mssql':
            qs = qs.group_by(*x_lookups).order_by(*x_lookup_names)
        else:
            qs = qs.group_by(*x_lookup_names).order_by(*x_lookup_names)

        return qs.limit(1000)


def queryset_search(qs, mapper, search):
    if isinstance(qs, MongoQueryset):
        for index in qs.query.list_indexes():
            if 'text' in index['key'].values():
                return qs.search(search)

        def map_column(column):
            if column.type in [data_types.INTEGER, data_types.FLOAT]:
                try:
                    return column.__eq__(int(search))
                except:
                    pass
            elif column.type in [data_types.BINARY]:
                try:
                    return column.__eq__(ObjectId(search))
                except:
                    pass
            elif column.type in [data_types.CHAR, data_types.TEXT]:
                return column.ilike('%{}%'.format(search))

        operators = list(filter(lambda x: x is not None, map(map_column, mapper.columns)))

        if len(operators) > 1:
            return qs.filter(MongoOperator('or', operators))
        elif len(operators) == 1:
            return qs.filter(operators[0])
        else:
            return qs.filter(mapper.columns['_id'].exists(False))
    else:
        def map_column(column):
            if isinstance(column.type, (sqlalchemy.Integer, sqlalchemy.Numeric)):
                return cast(column, sqlalchemy.String).__eq__(search)
            elif isinstance(column.type, (sqlalchemy.JSON, sqlalchemy.Enum)):
                return cast(column, sqlalchemy.String).ilike('%{}%'.format(search))
            elif isinstance(column.type, sqlalchemy.String):
                return cast(column, sqlalchemy.String).ilike('%{}%'.format(search))

        operators = list(filter(lambda x: x is not None, map(map_column, mapper.columns)))

        return qs.filter(or_(*operators))
