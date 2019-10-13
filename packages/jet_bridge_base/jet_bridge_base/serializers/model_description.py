from jet_bridge_base import fields as fields_
from jet_bridge_base.serializers.serializer import Serializer


class ModelDescriptionFieldSerializer(Serializer):
    name = fields_.CharField()
    db_column = fields_.CharField()
    field = fields_.CharField()
    filterable = fields_.BooleanField()
    null = fields_.BooleanField()
    editable = fields_.BooleanField()
    params = fields_.JSONField()
    verbose_name = fields_.CharField(required=False)
    required = fields_.BooleanField(required=False)
    editable = fields_.BooleanField(required=False)

    class Meta:
        fields = (
            'name',
            'db_column',
            'field',
            'filterable',
            'null',
            'editable',
            'params',
            'verbose_name',
            'required',
            'editable',
        )


class ModelDescriptionRelationSerializer(Serializer):
    name = fields_.CharField()
    related_model = fields_.JSONField()
    field = fields_.CharField()
    related_model_field = fields_.CharField()
    through = fields_.JSONField()

    class Meta:
        fields = (
            'name',
            'related_model',
            'field',
            'related_model_field',
            'through',
        )


class ModelDescriptionSerializer(Serializer):
    model = fields_.CharField()
    db_table = fields_.CharField()
    hidden = fields_.BooleanField()
    primary_key_field = fields_.CharField()
    fields = ModelDescriptionFieldSerializer(many=True)
    relations = ModelDescriptionRelationSerializer(many=True)
    verbose_name = fields_.CharField(required=False)
    verbose_name_plural = fields_.CharField(required=False)

    class Meta:
        fields = (
            'model',
            'db_table',
            'hidden',
            'fields',
            'relations',
            'primary_key_field',
            'verbose_name',
            'verbose_name_plural',
        )
