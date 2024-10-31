from jet_bridge_base.db_types import inspect_uniform
from jet_bridge_base.serializers.model_serializer import ModelSerializer


def get_model_serializer(Model):
    mapper = inspect_uniform(Model)

    class CustomModelSerializer(ModelSerializer):
        class Meta:
            model = Model
            model_fields = list(map(lambda x: x.key, mapper.columns))

    return CustomModelSerializer
