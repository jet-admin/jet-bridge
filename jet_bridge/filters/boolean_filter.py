from jet_bridge.fields import CharField, BooleanField
from jet_bridge.filters.filter import Filter


class BooleanFilter(Filter):
    field_class = BooleanField
