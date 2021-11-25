from sqlalchemy import func, sql

from jet_bridge_base.filters.char_filter import CharFilter
from jet_bridge_base.filters.filter import EMPTY_VALUES


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

class ModelGroupFilter(CharFilter):

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        x_column = getattr(self.model, value['x_column'])
        y_column = getattr(self.model, value['y_column'])
        y_func = get_query_func_by_name(value['y_func'], y_column)

        if y_func is None:
            return qs.filter(sql.false())

        if value['x_lookup'] and value['x_lookup'] in ['date']:
            x_lookup = getattr(func, value['x_lookup'])(x_column)
        else:
            x_lookup = x_column

        whereclause = qs.whereclause
        qs = qs.session.query(x_lookup.label('group'), y_func.label('y_func'))

        if whereclause is not None:
            qs = qs.filter(whereclause)

        return qs.group_by('group').order_by('group')
