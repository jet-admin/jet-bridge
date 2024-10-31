from jet_bridge_base.db_types import queryset_aggregate
from jet_bridge_base.filters.char_filter import CharFilter
from jet_bridge_base.filters.filter import EMPTY_VALUES


class ModelAggregateFilter(CharFilter):

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        return queryset_aggregate(self.model, qs, value)
