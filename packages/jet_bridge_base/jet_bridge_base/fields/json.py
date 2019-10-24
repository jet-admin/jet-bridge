import json

from jet_bridge_base.fields.field import Field


class JSONField(Field):

    def to_internal_value_item(self, value):
        if isinstance(value, str):
            return json.loads(value)
        else:
            return value

    def to_representation_item(self, value):
        return value
