from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.utils.classes import is_instance_or_subclass
from sqlalchemy import func, sql, inspect
from sqlalchemy.sql import sqltypes, text

from jet_bridge_base.filters.char_filter import CharFilter
from jet_bridge_base.filters.filter import EMPTY_VALUES
from jet_bridge_base.utils.queryset import get_session_engine


def get_query_func_by_name(name, column):
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


def get_query_lookup_func_by_name(session, lookup_type, lookup_param, column):
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


class ModelGroupFilter(CharFilter):

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        x_columns = list(map(lambda x: getattr(self.model, x), value['x_columns']))
        y_column = getattr(self.model, value['y_column'])
        y_func = get_query_func_by_name(value['y_func'], y_column)

        if y_func is None:
            return qs.filter(sql.false())

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
                mapper = inspect(self.model)
                column = mapper.columns.get(column.name)
                if column is not None and not isinstance(column.type, (sqltypes.DateTime, sqltypes.Date)):
                    raise ValidationError('Can\'t apply date functions to non-date field: {}'.format(column.name))

            lookup = get_query_lookup_func_by_name(qs.session, lookup_type, lookup_param, column)
            return lookup.label(group_name(i))

        x_lookups = list(map(lambda x: map_lookup(x[1], x[0]), enumerate(x_columns)))
        x_lookup_names = list(map(lambda x: x.name, x_lookups))

        whereclause = qs.whereclause
        qs = qs.session.query(*x_lookups, y_func.label('y_func'))

        if whereclause is not None:
            qs = qs.filter(whereclause)

        if get_session_engine(qs.session) == 'mssql':
            return qs.group_by(*x_lookups).order_by(*x_lookup_names)
        else:
            return qs.group_by(*x_lookup_names).order_by(*x_lookup_names)
