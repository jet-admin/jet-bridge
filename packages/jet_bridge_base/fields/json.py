import json

from jet_bridge_base.fields.field import Field


class JSONField(Field):

    def to_internal_value_item(self, value):
        return json.loads(value)

    def to_representation_item(self, value):
        return value
