from sqlalchemy import inspect

from jet_bridge_base.db import get_mapped_base
from jet_bridge_base.exceptions.not_found import NotFound
from jet_bridge_base.filters.model import get_model_filter_class
from jet_bridge_base.filters.model_aggregate import ModelAggregateFilter
from jet_bridge_base.filters.model_group import ModelGroupFilter
from jet_bridge_base.permissions import HasProjectPermissions, ReadOnly
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.router import action
from jet_bridge_base.serializers.model import get_model_serializer
from jet_bridge_base.serializers.model_group import ModelGroupSerializer
from jet_bridge_base.serializers.reorder import get_reorder_serializer
from jet_bridge_base.serializers.reset_order import get_reset_order_serializer
from jet_bridge_base.utils.queryset import apply_default_ordering
from jet_bridge_base.utils.siblings import get_model_siblings
from jet_bridge_base.views.mixins.model import ModelAPIViewMixin


class ModelViewSet(ModelAPIViewMixin):
    model = None
    permission_classes = (HasProjectPermissions, ReadOnly)

    def before_dispatch(self):
        super(ModelViewSet, self).before_dispatch()
        mapper = inspect(self.get_model())
        self.lookup_field = mapper.primary_key[0].name

    def on_finish(self):
        super(ModelViewSet, self).on_finish()
        self.model = None

    def required_project_permission(self):
        return {
            'permission_type': 'model',
            'permission_object': self.request.path_kwargs['model'],
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
                'reset_order': 'w',
                'get_siblings': 'r'
            }.get(self.action, 'w')
        }

    def get_model(self):
        MappedBase = get_mapped_base(self.request)

        if self.model:
            return self.model

        if self.request.path_kwargs['model'] not in MappedBase.classes:
            raise NotFound

        self.model = MappedBase.classes[self.request.path_kwargs['model']]

        return self.model

    def get_serializer_class(self):
        Model = self.get_model()
        return get_model_serializer(Model)

    def get_filter_class(self):
        return get_model_filter_class(self.request, self.get_model())

    def get_queryset(self):
        Model = self.get_model()

        return self.session.query(Model)

    def filter_queryset(self, queryset):
        queryset = super(ModelViewSet, self).filter_queryset(queryset)
        if self.action == 'list':
            queryset = apply_default_ordering(queryset)
        return queryset

    @action(methods=['get'], detail=False)
    def aggregate(self, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        y_func = self.request.get_argument('_y_func').lower()
        y_column = self.request.get_argument('_y_column', self.lookup_field)

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

        return JSONResponse({
            'y_func': result
        })

    @action(methods=['get'], detail=False)
    def group(self, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        x_column = self.request.get_argument('_x_column')
        x_lookup_name = self.request.get_argument('_x_lookup', None)
        y_func = self.request.get_argument('_y_func').lower()
        y_column = self.request.get_argument('_y_column', self.lookup_field)

        model_serializer = self.get_serializer()

        # x_serializers = list(filter(lambda x: x.field_name == x_column, model_serializer.fields))
        # x_serializer = x_serializers[0]

        # y_serializers = list(filter(lambda x: x.field_name == y_column, model_serializer.fields))
        # y_serializer = y_serializers[0]

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

        return JSONResponse(serializer.representation_data)

    @action(methods=['post'], detail=False)
    def reorder(self, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        ReorderSerializer = get_reorder_serializer(self.get_model(), queryset, self.session)

        serializer = ReorderSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return JSONResponse(serializer.representation_data)

    @action(methods=['post'], detail=False)
    def reset_order(self, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        ResetOrderSerializer = get_reset_order_serializer(self.get_model(), queryset, self.session)

        serializer = ResetOrderSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return JSONResponse(serializer.representation_data)

    @action(methods=['get'], detail=True)
    def get_siblings(self, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        obj = self.get_object()

        return JSONResponse(get_model_siblings(self.request, self.model, obj, queryset))
