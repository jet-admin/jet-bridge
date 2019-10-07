import six

from jet_bridge_base.fields.field import Field


class CharField(Field):

    def __init__(self, *args, **kwargs):
        self.trim_whitespace = kwargs.pop('trim_whitespace', True)
        super(CharField, self).__init__(*args, **kwargs)

    def to_internal_value_item(self, value):
        if value is None:
            return
        value = six.text_type(value)
        return value.strip() if self.trim_whitespace else value

    def to_representation_item(self, value):
        if value is None:
            return
        return six.text_type(value)
