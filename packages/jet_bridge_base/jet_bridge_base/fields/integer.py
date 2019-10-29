import six

from jet_bridge_base.fields.field import Field


class IntegerField(Field):
    field_error_messages = {
        'invalid': 'not a valid integer'
    }

    def to_internal_value_item(self, value):
        if value is None:
            return
        value = six.text_type(value).strip()

        try:
            return int(value)
        except (ValueError, TypeError):
            self.error('invalid')

    def to_representation_item(self, value):
        if value is None:
            return
        return six.text_type(value)
