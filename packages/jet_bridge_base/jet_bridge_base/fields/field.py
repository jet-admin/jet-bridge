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

        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, 'field_error_messages', {}))
        self.error_messages = messages

    def validate(self, value):
        return value

    def get_value(self, data):
        try:
            if isinstance(data, Mapping):
                field_value = data[self.field_name]
            else:
                field_value = getattr(data, self.field_name)
        except (KeyError, AttributeError):
            return empty

        if not getattr(self, 'many', False) and isinstance(field_value, list):
            field_value = field_value[0]

        if isinstance(field_value, bytes):
            field_value = field_value.decode('utf8')

        return field_value

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
