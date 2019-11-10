from __future__ import absolute_import
import json

from jet_bridge_base.fields.field import Field


class ArrayField(Field):
    field_error_messages = {
        'invalid': 'not a valid array'
    }

    def to_internal_value_item(self, value):
        try:
            result = json.loads(value)
            if not isinstance(result, list):
                raise ValueError
            return result
        except ValueError:
            self.error('invalid')

    def to_representation_item(self, value):
        return json.dumps(value)
