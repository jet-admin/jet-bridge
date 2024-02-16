import dateparser
import six

from jet_bridge_base.db import get_default_timezone
from jet_bridge_base.fields.field import Field


def datetime_apply_default_timezone(value, request):
    if value.tzinfo is not None:
        return value

    default_timezone = get_default_timezone(request) if request else None
    if default_timezone is None:
        return value

    return value.replace(tzinfo=default_timezone)


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

        request = self.context.get('request')
        value = datetime_apply_default_timezone(value, request)

        return value.isoformat()
