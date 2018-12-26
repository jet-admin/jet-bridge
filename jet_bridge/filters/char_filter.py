from jet_bridge.fields import CharField
from jet_bridge.filters.filter import Filter


class CharFilter(Filter):
    field_class = CharField
