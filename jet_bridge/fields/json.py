import json

from jet_bridge.fields.field import Field


class JSONField(Field):

    def __init__(self, *args, **kwargs):
        super(JSONField, self).__init__(*args, **kwargs)

    def to_internal_value_item(self, value):
        return json.loads(value)

    def to_representation_item(self, value):
        return value
