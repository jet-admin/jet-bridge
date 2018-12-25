from jet_bridge.fields import field, CharField
from jet_bridge.filters import lookups

EMPTY_VALUES = ([], (), {}, '', None)


class Filter(object):
    field_class = field
    lookup_operators = {
        lookups.EXACT: {'operator': '__eq__'},
        lookups.ICONTAINS: {'operator': 'ilike', 'transform': '%{}%'},
    }

    def __init__(self, field_name=None, model=None, lookup=lookups.DEFAULT_LOOKUP):
        self.field_name = field_name
        self.name = field_name
        self.model = model
        self.lookup = lookup

    def clean_value(self, value):
        if value is None:
            return
        return self.field_class().to_internal_value(value)

    def apply_lookup(self, qs, lookup, value):
        model_field = getattr(self.model, self.field_name)
        lookup_operator = self.lookup_operators[lookup]
        operator = lookup_operator['operator']
        transform = lookup_operator.get('transform')

        if transform:
            value = transform.format(value)

        return qs.filter(getattr(model_field, operator)(value))

    def filter(self, qs, value):
        value = self.clean_value(value)
        if value in EMPTY_VALUES:
            return qs
        return self.apply_lookup(qs, self.lookup, value)
