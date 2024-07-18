import six

from jet_bridge_base.fields.field import Field


class FloatField(Field):
    field_error_messages = {
        'invalid': 'not a valid float'
    }

    def to_internal_value_item(self, value):
        if value is None:
            return
        value = six.text_type(value).strip()

        if value.lower() == 'true':
            return 1
        elif value.lower() == 'false':
            return 0

        try:
            return float(value)
        except (ValueError, TypeError):
            self.error('invalid')

    def to_representation_item(self, value):
        if value is None:
            return
        return value
