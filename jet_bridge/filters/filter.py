from jet_bridge.fields import field, CharField, BooleanField
from jet_bridge.filters import lookups

EMPTY_VALUES = ([], (), {}, '', None)


class Filter(object):
    field_class = field
    lookup_operators = {
        lookups.EXACT: {'operator': '__eq__'},
        lookups.GT: {'operator': '__gt__'},
        lookups.GTE: {'operator': '__ge__'},
        lookups.LT: {'operator': '__lt__'},
        lookups.LTE: {'operator': '__le__'},
        lookups.ICONTAINS: {'operator': 'ilike', 'post_process': lambda x: '%{}%'.format(x)},
        lookups.IN: {'operator': 'in_', 'field_class': CharField, 'field_kwargs': {'many': True}, 'pre_process': lambda x: x.split(',')},
        lookups.STARTS_WITH: {'operator': 'ilike', 'post_process': lambda x: '{}%'.format(x)},
        lookups.ENDS_WITH: {'operator': 'ilike', 'post_process': lambda x: '%{}'.format(x)},
        lookups.IS_NULL: {'operator': lambda x: ('__eq__', None) if x else ('isnot', None), 'field_class': BooleanField}
    }

    def __init__(self, field_name=None, model=None, lookup=lookups.DEFAULT_LOOKUP):
        self.field_name = field_name
        self.name = field_name
        self.model = model
        self.lookup = lookup

    def clean_value(self, value):
        return value

    def apply_lookup(self, qs, lookup, value):
        model_field = getattr(self.model, self.field_name)
        lookup_operator = self.lookup_operators[lookup]
        operator = lookup_operator['operator']
        pre_process = lookup_operator.get('pre_process')
        post_process = lookup_operator.get('post_process')
        field_class = lookup_operator.get('field_class')
        field_kwargs = lookup_operator.get('field_kwargs', {})

        if pre_process:
            value = pre_process(value)

        if field_class:
            value = field_class(**field_kwargs).to_internal_value(value)

        if post_process:
            value = post_process(value)

        if callable(operator):
            op = operator(value)
            return qs.filter(getattr(model_field, op[0])(op[1]))
        else:
            return qs.filter(getattr(model_field, operator)(value))

    def filter(self, qs, value):
        value = self.clean_value(value)
        if value in EMPTY_VALUES:
            return qs
        return self.apply_lookup(qs, self.lookup, value)
