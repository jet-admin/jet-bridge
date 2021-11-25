from sqlalchemy import func, sql

from jet_bridge_base.filters.char_filter import CharFilter
from jet_bridge_base.filters.filter import EMPTY_VALUES
from jet_bridge_base.filters.model_group import get_query_func_by_name


class ModelAggregateFilter(CharFilter):

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        y_column = getattr(self.model, value['y_column'])
        y_func = get_query_func_by_name(value['y_func'], y_column)

        if y_func is None:
            return qs.filter(sql.false())

        whereclause = qs.whereclause
        qs = qs.session.query(y_func)

        if whereclause is not None:
            qs = qs.filter(whereclause)

        return qs
