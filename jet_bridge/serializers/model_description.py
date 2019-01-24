from jet_bridge import fields
from jet_bridge.serializers.serializer import Serializer


class ModelDescriptionFieldSerializer(Serializer):
    name = fields.CharField()
    db_column = fields.CharField()
    field = fields.CharField()
    filterable = fields.BooleanField()
    editable = fields.BooleanField()
    params = fields.JSONField()

    class Meta:
        fields = (
            'name',
            'db_column',
            'field',
            'filterable',
            'editable',
            'params',
        )


class ModelDescriptionRelationSerializer(Serializer):
    name = fields.CharField()
    related_model = fields.JSONField()
    field = fields.CharField()
    related_model_field = fields.CharField()
    through = fields.JSONField()

    class Meta:
        fields = (
            'name',
            'related_model',
            'field',
            'related_model_field',
            'through',
        )


class ModelDescriptionSerializer(Serializer):
    model = fields.CharField()
    db_table = fields.CharField()
    hidden = fields.BooleanField()
    primary_key_field = fields.CharField()
    fields = ModelDescriptionFieldSerializer(many=True)
    relations = ModelDescriptionRelationSerializer(many=True)

    class Meta:
        fields = (
            'model',
            'db_table',
            'hidden',
            'fields',
            'relations',
            'primary_key_field',
        )
