from __future__ import absolute_import
import json

from six import string_types

from jet_bridge_base.fields.field import Field


class JSONField(Field):
    field_error_messages = {
        'invalid': 'not a valid JSON'
    }

    def __init__(self, *args, **kwargs):
        if 'allow_many' not in kwargs:
            kwargs['allow_many'] = True
        super(JSONField, self).__init__(*args, **kwargs)

    def to_internal_value_item(self, value):
        if isinstance(value, string_types):
            try:
                return json.loads(value)
            except ValueError:
                self.error('invalid')
        else:
            return value

    def to_representation_item(self, value):
        return value
