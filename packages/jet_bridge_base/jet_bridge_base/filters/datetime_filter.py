
from jet_bridge_base.fields.datetime import DateTimeField
from jet_bridge_base.filters.filter import Filter


class DateTimeFilter(Filter):
    field_class = DateTimeField
