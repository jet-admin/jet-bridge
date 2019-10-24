from jet_bridge_base.fields import CharField
from jet_bridge_base.serializers.serializer import Serializer


class ModelGroupSerializer(Serializer):
    group = CharField()
    y_func = CharField()  # TODO: change to integer default

    def __init__(self, *args, **kwargs):
        if 'group_serializer' in kwargs:
            self.fields['group'] = kwargs.pop('group_serializer')

        if 'y_func_serializer' in kwargs:
            self.fields['y_func'] = kwargs.pop('y_func_serializer')

        super(ModelGroupSerializer, self).__init__(*args, **kwargs)

