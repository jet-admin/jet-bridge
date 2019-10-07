from jet_bridge_base.fields import CharField
from jet_bridge_base.filters.filter import Filter


class CharFilter(Filter):
    field_class = CharField
