from sqlalchemy import func, sql

from jet_bridge_base.filters.char_filter import CharFilter
from jet_bridge_base.filters.filter import EMPTY_VALUES


class ModelGroupFilter(CharFilter):

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        x_column = getattr(self.model, value['x_column'])
        y_column = getattr(self.model, value['y_column'])

        if value['y_func'] == 'count':
            y_func = func.count(y_column)
        elif value['y_func'] == 'sum':
            y_func = func.sum(y_column)
        elif value['y_func'] == 'min':
            y_func = func.min(y_column)
        elif value['y_func'] == 'max':
            y_func = func.max(y_column)
        elif value['y_func'] == 'avg':
            y_func = func.avg(y_column)
        else:
            return qs.filter(sql.false())

        if value['x_lookup'] and value['x_lookup'] in ['date']:
            x_lookup = getattr(func, value['x_lookup'])
            x_func = x_lookup(x_column)
        else:
            x_func = x_column

        qs = qs.session.query(x_func.label('group'), y_func.label('y_func')).group_by('group').order_by('group').all()

        return qs
