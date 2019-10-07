import six

from jet_bridge_base.fields.field import Field


class IntegerField(Field):

    def to_internal_value_item(self, value):
        if value is None:
            return
        value = six.text_type(value)
        return int(value.strip())

    def to_representation_item(self, value):
        if value is None:
            return
        return six.text_type(value)
