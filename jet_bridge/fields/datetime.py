import dateparser
import six

from jet_bridge.fields.field import Field


class DateTimeField(Field):

    def __init__(self, *args, **kwargs):
        super(DateTimeField, self).__init__(*args, **kwargs)

    def to_internal_value_item(self, value):
        if value is None:
            return
        value = six.text_type(value)
        return dateparser.parse(value.strip())

    def to_representation_item(self, value):
        if value is None:
            return
        return value.isoformat()
