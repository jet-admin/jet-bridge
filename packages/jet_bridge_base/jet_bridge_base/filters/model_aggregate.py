from sqlalchemy import func, sql

from jet_bridge_base.filters.char_filter import CharFilter
from jet_bridge_base.filters.filter import EMPTY_VALUES


class ModelAggregateFilter(CharFilter):

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

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

        qs = qs.session.query(y_func).one()

        return qs
