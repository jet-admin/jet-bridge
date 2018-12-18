import six

from fields.field import Field


class CharField(Field):

    def __init__(self, *args, **kwargs):
        self.trim_whitespace = kwargs.pop('trim_whitespace', True)
        super().__init__(*args, **kwargs)

    def to_internal_value(self, value):
        value = six.text_type(value)
        return value.strip() if self.trim_whitespace else value

    def to_representation(self, value):
        return six.text_type(value)
