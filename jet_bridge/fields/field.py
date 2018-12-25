from collections import Mapping


class Field(object):
    field_name = None

    def __init__(self, *args, **kwargs):
        self.required = kwargs.pop('required', True)
        self.read_only = kwargs.pop('read_only', False)
        self.write_only = kwargs.pop('write_only', False)
        self.many = kwargs.pop('many', False)

    def validate(self, value):
        return value

    def get_value(self, data):
        try:
            if isinstance(data, Mapping):
                field_value = data[self.field_name]
            else:
                field_value = getattr(data, self.field_name)
        except (KeyError, AttributeError):
            return

        if not getattr(self, 'many', False) and isinstance(field_value, list):
            field_value = field_value[0]

        if isinstance(field_value, bytes):
            field_value = field_value.decode('utf8')

        return field_value

    def run_validation(self, value):
        value = self.to_internal_value(value)
        return value

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
            return list(map(lambda x: self.to_representation_item(x), value))
        else:
            return self.to_representation_item(value)
