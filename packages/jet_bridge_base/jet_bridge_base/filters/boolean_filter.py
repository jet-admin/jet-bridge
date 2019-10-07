from jet_bridge_base.fields import CharField, BooleanField
from jet_bridge_base.filters.filter import Filter


class BooleanFilter(Filter):
    field_class = BooleanField
