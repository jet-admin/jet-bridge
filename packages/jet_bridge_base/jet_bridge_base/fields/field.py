import six

try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

from jet_bridge_base.exceptions.validation_error import ValidationError


class empty:
    """
    This class is used to represent no data being provided for a given input
    or output value.

    It is required because `None` may be a valid input or output value.
    """
    pass


class Field(object):
    creation_counter = 0
    field_name = None
    field_error_messages = {
        'required': 'this field is required',
        'null': 'this field may not be null'
    }

    def __init__(self, *args, **kwargs):
        self.creation_counter = Field.creation_counter
        Field.creation_counter += 1

        self.required = kwargs.pop('required', True)
        self.read_only = kwargs.pop('read_only', False)
        self.write_only = kwargs.pop('write_only', False)
        self.many = kwargs.pop('many', False)
        self.allow_many = kwargs.pop('allow_many', False)
        self.default = kwargs.pop('default', empty)
        self.context = kwargs.pop('context', {})

        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, 'field_error_messages', {}))
        self.error_messages = messages

    def validate(self, value):
        return value

    def get_default(self):
        if callable(self.default):
            return self.default()
        return self.default

    def get_value(self, data):
        try:
            if isinstance(data, Mapping):
                field_value = data[self.field_name]
            else:
                field_value = getattr(data, self.field_name)
        except (KeyError, AttributeError):
            if self.default is not empty:
                return self.get_default()
            else:
                return empty

        if not getattr(self, 'many', False) and not getattr(self, 'allow_many', False) and isinstance(field_value, list):
            field_value = self.get_non_array_value(field_value)

        if isinstance(field_value, bytes):
            field_value = field_value.decode('utf8')

        return field_value

    def get_non_array_value(self, array_value):
        result = []

        for value in array_value:
            if value is None:
                continue
            str_value = six.text_type(value)
            result.append(str_value)

        return ','.join(result)

    def run_validation(self, value):
        if value is empty:
            if self.required:
                # raise ValidationError('Field is required')
                self.error('required')
            else:
                return None
        return self.to_internal_value(value)

    def to_internal_value_item(self, value):
        raise NotImplementedError

    def to_internal_value(self, value):
        if self.many:
            if value is empty:
                return []
            return list(map(lambda x: self.to_internal_value_item(x), value))
        else:
            return self.to_internal_value_item(value)

    def to_representation_item(self, value):
        raise NotImplementedError

    def to_representation(self, value):
        if self.many:
            return list(map(lambda x: self.to_representation_item(x), value or []))
        else:
            return self.to_representation_item(value)

    def error(self, key, **kwargs):
        """
        A helper method that simply raises a validation error.
        """
        try:
            msg = self.error_messages[key]
        except KeyError:
            class_name = self.__class__.__name__
            raise AssertionError('Error with key={} is not found for class={}'.format(key, class_name))
        message_string = msg.format(**kwargs)
        raise ValidationError(message_string, code=key)
