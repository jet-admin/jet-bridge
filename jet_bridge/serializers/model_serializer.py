from jet_bridge.serializers.serializer import Serializer


class ModelSerializer(Serializer):

    def __init__(self, *args, **kwargs):
        self.session = kwargs.get('context', {}).get('session', None)
        super(ModelSerializer, self).__init__(*args, **kwargs)

    def create(self, validated_data):
        ModelClass = self.meta.model

        instance = ModelClass(**validated_data)
        self.session.add(instance)
        self.session.commit()

        return instance

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        self.session.commit()

        return instance
