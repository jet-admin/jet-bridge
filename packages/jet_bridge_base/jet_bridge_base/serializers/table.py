from jet_bridge_base import fields
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.serializers.serializer import Serializer


class TableColumnSerializer(Serializer):
    name = fields.CharField()
    field = fields.CharField()
    db_field = fields.CharField(required=False)
    primary_key = fields.BooleanField(required=False)
    null = fields.BooleanField(required=False)
    default_type = fields.CharField(required=False)
    default_value = fields.RawField(required=False)
    params = fields.RawField(required=False)


class TableSerializer(Serializer):
    name = fields.CharField()
    columns = TableColumnSerializer(many=True)

    def validate(self, attrs):
        if not any(map(lambda x: x.get('primary_key'), attrs['columns'])):
            raise ValidationError('No primary key specified')
        return attrs