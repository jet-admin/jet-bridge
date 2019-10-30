from jet_bridge_base.fields.field import Field


class AnyField(Field):

    def to_internal_value_item(self, value):
        return value

    def to_representation_item(self, value):
        return value
