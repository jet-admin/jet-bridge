from jet_bridge_base.utils.queryset import get_session_engine
from sqlalchemy import Unicode
from sqlalchemy.dialects.postgresql import JSON, ENUM
from six import string_types

from jet_bridge_base.fields import field, CharField, BooleanField
from jet_bridge_base.filters import lookups

EMPTY_VALUES = ([], (), {}, None)


def safe_startswith(column, value):
    field_type = column.property.columns[0].type if hasattr(column, 'property') else None

    if isinstance(field_type, ENUM) or field_type is None:
        return column.cast(Unicode).ilike('{}%'.format(value))
    else:
        return column.ilike('{}%'.format(value))


def safe_endswith(column, value):
    field_type = column.property.columns[0].type if hasattr(column, 'property') else None

    if isinstance(field_type, ENUM) or field_type is None:
        return column.cast(Unicode).ilike('%{}'.format(value))
    else:
        return column.ilike('%{}'.format(value))


def safe_icontains(column, value):
    field_type = column.property.columns[0].type if hasattr(column, 'property') else None

    if isinstance(field_type, ENUM) or field_type is None:
        return column.cast(Unicode).ilike('%{}%'.format(value))
    else:
        return column.ilike('%{}%'.format(value))


def json_icontains(column, value):
    field_type = column.property.columns[0].type if hasattr(column, 'property') else None

    if isinstance(field_type, JSON) or field_type is None:
        return column.cast(Unicode).ilike('%{}%'.format(value))
    else:
        return column.astext.ilike('%{}%'.format(value))


def coveredby(column, value):
    return column.ST_CoveredBy(value)


def safe_array(value):
    if isinstance(value, list):
        return value
    elif isinstance(value, string_types):
        if value != '':
            return value.split(',')
        else:
            return []
    else:
        value


class Filter(object):
    field_class = field
    lookup_operators = {
        lookups.EXACT: {'operator': '__eq__'},
        lookups.GT: {'operator': '__gt__'},
        lookups.GTE: {'operator': '__ge__'},
        lookups.LT: {'operator': '__lt__'},
        lookups.LTE: {'operator': '__le__'},
        lookups.ICONTAINS: {'operator': False, 'func': safe_icontains},
        lookups.IN: {'operator': 'in_', 'field_class': CharField, 'field_kwargs': {'many': True}, 'pre_process': lambda x: safe_array(x)},
        lookups.STARTS_WITH: {'operator': False, 'func': safe_startswith},
        lookups.ENDS_WITH: {'operator': False, 'func': safe_endswith},
        lookups.IS_NULL: {'operator': lambda x: ('__eq__', None) if x else ('isnot', None), 'field_class': BooleanField},
        lookups.JSON_ICONTAINS: {'operator': False, 'func': json_icontains},
        lookups.COVEREDBY: {'operator': False, 'func': coveredby}
    }

    def __init__(self, name=None, column=None, lookup=lookups.DEFAULT_LOOKUP, exclude=False):
        self.name = name
        self.column = column
        self.lookup = lookup
        self.exclude = exclude

    def clean_value(self, value):
        return value

    def get_loookup_criterion(self, value):
        lookup_operator = self.lookup_operators[self.lookup]
        operator = lookup_operator['operator']
        pre_process = lookup_operator.get('pre_process')
        post_process = lookup_operator.get('post_process')
        field_class = lookup_operator.get('field_class')
        field_kwargs = lookup_operator.get('field_kwargs', {})
        func = lookup_operator.get('func')

        if pre_process:
            value = pre_process(value)

        if field_class:
            value = field_class(**field_kwargs).to_internal_value(value)

        if post_process:
            value = post_process(value)

        if func:
            return func(self.column, value)
        elif callable(operator):
            op = operator(value)

            if self.exclude:
                return ~getattr(self.column, op[0])(op[1])
            else:
                return getattr(self.column, op[0])(op[1])
        else:
            if self.exclude:
                return ~getattr(self.column, operator)(value)
            else:
                return getattr(self.column, operator)(value)

    def apply_lookup(self, qs, value):
        criterion = self.get_loookup_criterion(value)
        return qs.filter(criterion)

    def filter(self, qs, value):
        value = self.clean_value(value)
        if value in EMPTY_VALUES:
            return qs
        return self.apply_lookup(qs, value)
