import six

from jet_bridge.fields.field import Field


class IntegerField(Field):

    def __init__(self, *args, **kwargs):
        super(IntegerField, self).__init__(*args, **kwargs)

    def to_internal_value_item(self, value):
        if value is None:
            return
        value = six.text_type(value)
        return int(value.strip())

    def to_representation_item(self, value):
        if value is None:
            return
        return six.text_type(value)
