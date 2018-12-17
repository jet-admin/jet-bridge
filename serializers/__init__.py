from collections import OrderedDict

import six


class Field(object):
    field_name = None

    def __init__(self, *args, **kwargs):
        self.read_only = kwargs.pop('read_only', False)
        self.write_only = kwargs.pop('write_only', False)

    def validate(self, value):
        return value

    def run_validation(self, value):
        value = self.to_internal_value(value)
        return value

    def to_internal_value(self, value):
        raise NotImplementedError

    def to_representation(self, value):
        raise NotImplementedError


class CharField(Field):

    def __init__(self, *args, **kwargs):
        self.trim_whitespace = kwargs.pop('trim_whitespace', True)
        super().__init__(*args, **kwargs)

    def to_internal_value(self, value):
        value = six.text_type(value)
        return value.strip() if self.trim_whitespace else value

    def to_representation(self, value):
        return six.text_type(value)


class BooleanField(Field):
    TRUE_VALUES = {
        't', 'T',
        'y', 'Y', 'yes', 'YES',
        'true', 'True', 'TRUE',
        'on', 'On', 'ON',
        '1', 1,
        True
    }
    FALSE_VALUES = {
        'f', 'F',
        'n', 'N', 'no', 'NO',
        'false', 'False', 'FALSE',
        'off', 'Off', 'OFF',
        '0', 0, 0.0,
        False
    }

    def to_internal_value(self, value):
        if value in self.TRUE_VALUES:
            return True
        elif value in self.FALSE_VALUES:
            return False
        return bool(value)

    def to_representation(self, value):
        return value


class Serializer(Field):
    validated_data = None
    fields = []
    errors = None

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        self.data = kwargs.pop('data', None)
        self.many = kwargs.pop('many', False)
        self.meta = getattr(self, 'Meta')
        self.update_fields()
        super().__init__(*args, **kwargs)

    def update_fields(self):
        if not self.meta:
            return
        fields = []
        for field_name in self.meta.fields:
            assert hasattr(self, field_name), (
                'No such field %s for serializer %s' % (field_name, self.__class__.__name__)
            )
            field = getattr(self, field_name)
            field.field_name = field_name
            fields.append(field)
        self.fields = fields

    @property
    def readable_fields(self):
        return list(filter(lambda x: not x.write_only, self.fields))

    @property
    def writable_fields(self):
        return list(filter(lambda x: not x.read_only, self.fields))

    def run_validation(self, value):
        value = self.to_internal_value(value)
        return value

    def is_valid(self, raise_exception=False):
        try:
            self.validated_data = self.run_validation(self.data)
            self.errors = None
        except Exception as e:
            self.validated_data = None
            self.errors = e

        if self.errors and raise_exception:
            raise Exception(self.errors)

        return not bool(self.errors)

    def to_internal_value(self, value):
        result = OrderedDict()
        errors = OrderedDict()

        for field in self.writable_fields:
            field_value = value[field.field_name]

            try:
                validated_value = field.run_validation(field_value)
                result[field.field_name] = validated_value
            except Exception as e:
                errors[field.field_name] = str(e)

        if errors:
            raise Exception(errors)

        return result

    def to_representation_item(self, value):
        result = OrderedDict()

        for field in self.readable_fields:
            field_value = value[field.field_name]
            result[field.field_name] = field.to_representation(field_value)

        return result

    def to_representation(self, value):
        if self.many:
            return list(map(lambda x: self.to_representation_item(x), value))
        else:
            return self.to_representation_item(value)

    @property
    def representation_data(self):
        if self.validated_data:
            return self.to_representation(self.validated_data)
        elif self.instance:
            return self.to_representation(self.instance)

    def save(self):
        pass
