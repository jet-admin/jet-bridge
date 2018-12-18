
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
