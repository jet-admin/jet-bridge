from __future__ import absolute_import
import json
from six import string_types

from jet_bridge_base.fields.field import Field


class ArrayField(Field):
    field_error_messages = {
        'invalid': 'not a valid array'
    }

    def to_internal_value_item(self, value):
        internal_value = None

        if isinstance(value, string_types):
            try:
                internal_value = json.loads(value)
            except ValueError:
                self.error('invalid')
        else:
            internal_value = value

        if not isinstance(internal_value, list):
            raise ValueError

        return internal_value

    def to_representation_item(self, value):
        return value
