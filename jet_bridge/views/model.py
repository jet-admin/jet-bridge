from jet_bridge.filters.model import get_model_filter_class
from jet_bridge.permissions import HasProjectPermissions, ModifyNotInDemo
from jet_bridge.serializers.model import get_model_serializer
from jet_bridge.views.mixins.model import ModelAPIViewMixin
from jet_bridge.db import MappedBase


class ModelHandler(ModelAPIViewMixin):
    model = None
    permission_classes = (HasProjectPermissions, ModifyNotInDemo)

    @property
    def required_project_permission(self):
        return {
            'permission_type': 'model',
            'permission_object': self.path_kwargs['model'],
            'permission_actions': {
                'create': 'w',
                'update': 'w',
                'partial_update': 'w',
                'destroy': 'd',
                'retrieve': 'r',
                'list': 'r',
                'aggregate': 'r',
                'group': 'r',
                'reorder': 'w',
                'reset_order': 'w'
            }.get(self.action, 'w')
        }

    def get_model(self):
        if self.model:
            return self.model

        self.model = MappedBase.classes[self.path_kwargs['model']]

        return self.model

    def get_serializer_class(self):
        Model = self.get_model()
        return get_model_serializer(Model)

    def get_filter_class(self):
        return get_model_filter_class(self.get_model())

    def get_queryset(self):
        Model = self.get_model()

        return self.session.query(Model)
