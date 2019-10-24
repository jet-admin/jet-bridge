import dateparser
import six

from jet_bridge_base.fields.field import Field


class DateTimeField(Field):

    def to_internal_value_item(self, value):
        if value is None:
            return
        value = six.text_type(value)
        return dateparser.parse(value.strip())

    def to_representation_item(self, value):
        if value is None:
            return
        return value.isoformat()
