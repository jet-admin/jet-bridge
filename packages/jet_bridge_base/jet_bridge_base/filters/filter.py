import json

from jet_bridge_base.db_types import get_session_engine, MongoColumn
from jet_bridge_base.serializers.model_serializer import get_column_data_type
from jet_bridge_base.utils.classes import is_instance_or_subclass
from sqlalchemy import Unicode, and_, or_
from sqlalchemy.dialects.postgresql import ENUM, JSONB, array
from sqlalchemy.sql import sqltypes
from six import string_types

from jet_bridge_base.fields import field, BooleanField, CharField
from jet_bridge_base.filters import lookups

EMPTY_VALUES = ([], (), {}, '', None)


def safe_is_float(value):
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def safe_equals(queryset, column, value):
    if isinstance(column, MongoColumn):
        return column.__eq__(value)
    else:
        field_type = column.property.columns[0].type if hasattr(column, 'property') else column.type

        if is_instance_or_subclass(field_type, (sqltypes.JSON,)):
            if get_session_engine(queryset.session) == 'postgresql':
                value_str = json.dumps(str(value))
                operators = [column.cast(JSONB).op('@>')(value_str)]

                if safe_is_float(value):
                    operators.append(column.cast(JSONB).op('@>')(value))

                return or_(*operators)
            else:
                return column.cast(Unicode).ilike('%{}%'.format(value))
        else:
            return column.__eq__(value)


def safe_in(queryset, column, value):
    if isinstance(column, MongoColumn):
        return column.in_(value)
    else:
        field_type = column.property.columns[0].type if hasattr(column, 'property') else column.type

        if is_instance_or_subclass(field_type, (sqltypes.JSON,)):
            if get_session_engine(queryset.session) == 'postgresql':
                operators = []

                for value_item in value:
                    value_item_str = json.dumps(value_item)
                    operators.append(column.cast(JSONB).op('@>')(value_item_str))

                    if safe_is_float(value_item):
                        operators.append(column.cast(JSONB).op('@>')(value_item))

                return or_(*operators)
            else:
                operators = list(map(lambda x: column.cast(Unicode).ilike('%{}%'.format(x)), value))
                return or_(*operators)
        else:
            return column.in_(value)


def safe_startswith(queryset, column, value):
    if isinstance(column, MongoColumn):
        return column.ilike('{}%'.format(value))
    else:
        field_type = column.property.columns[0].type if hasattr(column, 'property') else column.type

        if is_instance_or_subclass(field_type, (ENUM, sqltypes.NullType)):
            return column.cast(Unicode).ilike('{}%'.format(value))
        else:
            return column.ilike('{}%'.format(value))


def safe_endswith(queryset, column, value):
    if isinstance(column, MongoColumn):
        return column.ilike('%{}'.format(value))
    else:
        field_type = column.property.columns[0].type if hasattr(column, 'property') else column.type

        if is_instance_or_subclass(field_type, (ENUM, sqltypes.NullType)):
            return column.cast(Unicode).ilike('%{}'.format(value))
        else:
            return column.ilike('%{}'.format(value))


def safe_icontains(queryset, column, value):
    if isinstance(column, MongoColumn):
        return column.ilike('%{}%'.format(value))
    else:
        field_type = column.property.columns[0].type if hasattr(column, 'property') else column.type

        if is_instance_or_subclass(field_type, (ENUM, sqltypes.NullType)):
            return column.cast(Unicode).ilike('%{}%'.format(value))
        else:
            return column.ilike('%{}%'.format(value))


def json_icontains(queryset, column, value):
    if isinstance(column, MongoColumn):
        return column.json_icontains(value)
    else:
        field_type = column.property.columns[0].type if hasattr(column, 'property') else column.type

        if is_instance_or_subclass(field_type, (sqltypes.JSON, sqltypes.NullType)) or not hasattr(column, 'astext'):
            return column.cast(Unicode).ilike('%{}%'.format(value))
        else:
            return column.astext.ilike('%{}%'.format(value))


def is_null(queryset, column, value):
    if value:
        return column.__eq__(None)
    else:
        return column.isnot(None)


def is_empty(queryset, column, value):
    field_type = column.property.columns[0].type if hasattr(column, 'property') else column.type

    if is_instance_or_subclass(field_type, sqltypes.String):
        if value:
            return or_(column.__eq__(None), column == '')
        else:
            return and_(column.isnot(None), column != '')
    else:
        return is_null(queryset, column, value)


def coveredby(queryset, column, value):
    return column.ST_CoveredBy(value)


def safe_not_array(value):
    if isinstance(value, list):
        if len(value):
            return value[0]
        else:
            return ''
    else:
        return value


def safe_array(value):
    if isinstance(value, list):
        return value
    elif isinstance(value, string_types):
        if value != '':
            return value.split(',')
        else:
            return []
    else:
        return [value]


class Filter(object):
    field_class = field
    lookup_operators = {
        lookups.EXACT: {'operator': False, 'func': safe_equals, 'pre_process': lambda x: safe_not_array(x)},
        lookups.GT: {'operator': '__gt__', 'pre_process': lambda x: safe_not_array(x)},
        lookups.GTE: {'operator': '__ge__', 'pre_process': lambda x: safe_not_array(x)},
        lookups.LT: {'operator': '__lt__', 'pre_process': lambda x: safe_not_array(x)},
        lookups.LTE: {'operator': '__le__', 'pre_process': lambda x: safe_not_array(x)},
        lookups.ICONTAINS: {'operator': False, 'func': safe_icontains, 'pre_process': lambda x: safe_not_array(x)},
        lookups.IN: {'operator': False, 'func': safe_in, 'field_kwargs': {'many': True}, 'pre_process': lambda x: safe_array(x)},
        lookups.STARTS_WITH: {'operator': False, 'func': safe_startswith, 'pre_process': lambda x: safe_not_array(x)},
        lookups.ENDS_WITH: {'operator': False, 'func': safe_endswith, 'pre_process': lambda x: safe_not_array(x)},
        lookups.IS_NULL: {'operator': False, 'func': is_null, 'field_class': BooleanField, 'pre_process': lambda x: safe_not_array(x)},
        lookups.IS_EMPTY: {'operator': False, 'func': is_empty, 'field_class': BooleanField, 'pre_process': lambda x: safe_not_array(x)},
        lookups.JSON_ICONTAINS: {'operator': False, 'func': json_icontains, 'field_class': CharField, 'pre_process': lambda x: safe_not_array(x)},
        lookups.COVEREDBY: {'operator': False, 'func': coveredby, 'pre_process': lambda x: safe_not_array(x)}
    }

    def __init__(self, name=None, column=None, lookup=lookups.DEFAULT_LOOKUP, exclude=False):
        self.name = name
        self.column = column
        self.lookup = lookup
        self.exclude = exclude

    def clean_value(self, value):
        return value

    def get_default_lookup_field_class(self):
        return get_column_data_type(self.column)

    def get_lookup_criterion(self, qs, value):
        lookup_operator = self.lookup_operators[self.lookup]
        operator = lookup_operator['operator']
        pre_process = lookup_operator.get('pre_process')
        post_process = lookup_operator.get('post_process')
        field_class = lookup_operator.get('field_class')
        field_kwargs = lookup_operator.get('field_kwargs', {})
        func = lookup_operator.get('func')

        if pre_process:
            value = pre_process(value)

        if not field_class:
            field_class = self.get_default_lookup_field_class()

        if value is not None:
            value = field_class(**field_kwargs).to_internal_value(value)

        if post_process:
            value = post_process(value)

        if func:
            if self.exclude:
                return ~func(qs, self.column, value)
            else:
                return func(qs, self.column, value)
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
        criterion = self.get_lookup_criterion(qs, value)
        return qs.filter(criterion)

    def filter(self, qs, value):
        value = self.clean_value(value)
        if value in EMPTY_VALUES:
            return qs
        return self.apply_lookup(qs, value)
