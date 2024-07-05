from jet_bridge_base import fields
from jet_bridge_base.fields import FloatField
from jet_bridge_base.filters.filter import Filter


class IntegerFilter(Filter):
    field_class = FloatField

    def get_default_lookup_field_class(self):
        return fields.FloatField
