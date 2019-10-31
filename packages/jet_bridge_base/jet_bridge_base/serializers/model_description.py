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
    default_type = fields_.CharField(required=False)
    default_value = fields_.AnyField(required=False)


# class ModelDescriptionRelationSerializer(Serializer):
#     name = fields_.CharField()
#     related_model = fields_.JSONField()
#     field = fields_.CharField()
#     related_model_field = fields_.CharField()
#     through = fields_.JSONField()


class ModelDescriptionSerializer(Serializer):
    model = fields_.CharField()
    db_table = fields_.CharField()
    hidden = fields_.BooleanField()
    primary_key_field = fields_.CharField()
    fields = ModelDescriptionFieldSerializer(many=True)
    # relations = ModelDescriptionRelationSerializer(many=True)
    verbose_name = fields_.CharField(required=False)
    verbose_name_plural = fields_.CharField(required=False)
    display_field = fields_.CharField(required=False)
    default_order_by = fields_.CharField(required=False)
