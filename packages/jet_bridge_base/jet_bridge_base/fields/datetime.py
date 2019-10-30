import dateparser
import six

from jet_bridge_base.fields.field import Field


class DateTimeField(Field):
    field_error_messages = {
        'invalid': 'date has wrong format'
    }

    def to_internal_value_item(self, value):
        if value is None:
            return
        value = six.text_type(value).strip()

        try:
            result = dateparser.parse(value)
        except ValueError:
            result = None

        if result is None:
            self.error('invalid')

        return result

    def to_representation_item(self, value):
        if value is None:
            return
        return value.isoformat()
