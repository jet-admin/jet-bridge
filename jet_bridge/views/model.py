from sqlalchemy import inspect

from jet_bridge.filters.model import get_model_filter_class
from jet_bridge.filters.model_aggregate import ModelAggregateFilter
from jet_bridge.filters.model_group import ModelGroupFilter
from jet_bridge.permissions import HasProjectPermissions, ModifyNotInDemo
from jet_bridge.responses.base import Response
from jet_bridge.router import action
from jet_bridge.serializers.model import get_model_serializer
from jet_bridge.serializers.model_group import ModelGroupSerializer
from jet_bridge.serializers.reorder import get_reorder_serializer
from jet_bridge.serializers.reset_order import get_reset_order_serializer
from jet_bridge.views.mixins.model import ModelAPIViewMixin
from jet_bridge.db import MappedBase


class ModelHandler(ModelAPIViewMixin):
    model = None
    permission_classes = (HasProjectPermissions, ModifyNotInDemo)

    def prepare(self):
        super(ModelHandler, self).prepare()
        mapper = inspect(self.get_model())
        self.lookup_field = mapper.primary_key[0].name

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

    @action(methods=['get'], detail=False)
    def aggregate(self, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        y_func = self.get_argument('_y_func').lower()
        y_column = self.get_argument('_y_column', self.lookup_field)

        model_serializer = self.get_serializer()

        y_serializers = list(filter(lambda x: x.field_name == y_column, model_serializer.fields))
        y_serializer = y_serializers[0]

        filter_instance = ModelAggregateFilter()
        filter_instance.model = self.model
        queryset = filter_instance.filter(queryset, {
            'y_func': y_func,
            'y_column': y_column
        })

        result = y_serializer.to_representation(queryset[0])  # TODO: Refactor serializer

        self.write_response(Response({
            'y_func': result
        }))

    @action(methods=['get'], detail=False)
    def group(self, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        x_column = self.get_argument('_x_column')
        x_lookup_name = self.get_argument('_x_lookup', None)
        y_func = self.get_argument('_y_func').lower()
        y_column = self.get_argument('_y_column', self.lookup_field)

        model_serializer = self.get_serializer()

        x_serializers = list(filter(lambda x: x.field_name == x_column, model_serializer.fields))
        x_serializer = x_serializers[0]

        y_serializers = list(filter(lambda x: x.field_name == y_column, model_serializer.fields))
        y_serializer = y_serializers[0]

        filter_instance = ModelGroupFilter()
        filter_instance.model = self.model
        queryset = filter_instance.filter(queryset, {
            'x_column': x_column,
            'x_lookup': x_lookup_name,
            'y_func': y_func,
            'y_column': y_column
        })
        serializer = ModelGroupSerializer(
            instance=queryset,
            many=True,
            # TODO: Refactor serializer
            # group_serializer=x_serializer,
            # y_func_serializer=y_serializer
        )

        self.write_response(Response(serializer.representation_data))

    @action(methods=['post'], detail=False)
    def reorder(self, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        ReorderSerializer = get_reorder_serializer(self.get_model(), queryset, self.session)

        serializer = ReorderSerializer(data=self.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.write_response(Response(serializer.representation_data))

    @action(methods=['post'], detail=False)
    def reset_order(self, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        ResetOrderSerializer = get_reset_order_serializer(self.get_model(), queryset, self.session)

        serializer = ResetOrderSerializer(data=self.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.write_response(Response(serializer.representation_data))
