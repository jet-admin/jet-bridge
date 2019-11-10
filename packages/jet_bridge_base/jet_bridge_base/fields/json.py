from __future__ import absolute_import
import json

from jet_bridge_base.fields.field import Field


class JSONField(Field):
    field_error_messages = {
        'invalid': 'not a valid JSON'
    }

    def to_internal_value_item(self, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except ValueError:
                self.error('invalid')
        else:
            return value

    def to_representation_item(self, value):
        return value
