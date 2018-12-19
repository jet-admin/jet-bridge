from collections import OrderedDict, Mapping

from fields.field import Field


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

        if hasattr(self.meta, 'fields'):
            for field_name in self.meta.fields:
                assert hasattr(self, field_name), (
                    'No such field %s for serializer %s' % (field_name, self.__class__.__name__)
                )
                field = getattr(self, field_name)
                field.field_name = field_name
                fields.append(field)

        if hasattr(self.meta, 'dynamic_fields'):
            for field_name, field in self.meta.dynamic_fields.items():
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
            if isinstance(value, Mapping):
                field_value = value[field.field_name]
            else:
                field_value = getattr(value, field.field_name)

            if not getattr(field, 'many', False) and isinstance(field_value, list):
                field_value = field_value[0]

            if isinstance(field_value, bytes):
                field_value = field_value.decode('utf8')

            validate_method = getattr(self, 'validate_' + field.field_name, None)

            try:
                validated_value = field.run_validation(field_value)
                if validate_method is not None:
                    validated_value = validate_method(validated_value)
                result[field.field_name] = validated_value
            except Exception as e:
                errors[field.field_name] = str(e)

        if errors:
            raise Exception(errors)

        return result

    def to_representation_item(self, value):
        result = OrderedDict()

        for field in self.readable_fields:
            if isinstance(value, Mapping):
                field_value = value[field.field_name]
            else:
                field_value = getattr(value, field.field_name)

            result[field.field_name] = field.to_representation(field_value)

        return result

    def to_representation(self, value):
        if self.many:
            return list(map(lambda x: self.to_representation_item(x), value))
        else:
            return self.to_representation_item(value)

    @property
    def representation_data(self):
        if self.validated_data is not None:
            return self.to_representation(self.validated_data)
        elif self.instance is not None:
            return self.to_representation(self.instance)

    def save(self):
        pass
