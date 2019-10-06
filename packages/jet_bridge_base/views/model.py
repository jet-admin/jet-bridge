from sqlalchemy import inspect, desc
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import UnaryExpression, AnnotatedColumnElement

from jet_bridge_base.filters.model import get_model_filter_class
from jet_bridge_base.filters.model_aggregate import ModelAggregateFilter
from jet_bridge_base.filters.model_group import ModelGroupFilter
from jet_bridge_base.permissions import HasProjectPermissions, ModifyNotInDemo
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.router import action
from jet_bridge_base.serializers.model import get_model_serializer
from jet_bridge_base.serializers.model_group import ModelGroupSerializer
from jet_bridge_base.serializers.reorder import get_reorder_serializer
from jet_bridge_base.serializers.reset_order import get_reset_order_serializer
from jet_bridge_base.utils.siblings import get_model_siblings
from jet_bridge_base.views.mixins.model import ModelAPIViewMixin
from jet_bridge_base.db import MappedBase


class ModelView(ModelAPIViewMixin):
    model = None
    permission_classes = (HasProjectPermissions, ModifyNotInDemo)

    def prepare(self):
        super(ModelView, self).prepare()
        mapper = inspect(self.get_model())
        self.lookup_field = mapper.primary_key[0].name

    def on_finish(self):
        super(ModelView, self).on_finish()
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
                'reset_order': 'w'
            }.get(self.action, 'w')
        }

    def get_model(self):
        if self.model:
            return self.model

        self.model = MappedBase.classes[self.request.path_kwargs['model']]

        return self.model

    def get_serializer_class(self):
        Model = self.get_model()
        return get_model_serializer(Model)

    def get_filter_class(self):
        return get_model_filter_class(self.get_model())

    def get_queryset(self):
        Model = self.get_model()

        return self.session.query(Model)

    def filter_queryset(self, queryset):
        queryset = super(ModelView, self).filter_queryset(queryset)
        if self.action == 'list':
            mapper = inspect(self.model)
            pk = mapper.primary_key[0].name
            context = queryset._compile_context()
            ordering = context.order_by

            def is_pk(x):
                if isinstance(x, AnnotatedColumnElement):
                    return x.name == pk
                elif isinstance(x, UnaryExpression):
                    return x.element.name == pk and x.modifier == operators.desc_op
                return False

            if ordering is None or not any(map(is_pk, ordering)):
                order_by = list(ordering or []) + [desc(pk)]
                queryset = queryset.order_by(*order_by)
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

        serializer = ReorderSerializer(data=self.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return JSONResponse(serializer.representation_data)

    @action(methods=['post'], detail=False)
    def reset_order(self, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        ResetOrderSerializer = get_reset_order_serializer(self.get_model(), queryset, self.session)

        serializer = ResetOrderSerializer(data=self.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return JSONResponse(serializer.representation_data)

    @action(methods=['get'], detail=True)
    def get_siblings(self, *args, **kwargs):
        lookup_url_kwarg = self.lookup_url_kwarg or 'pk'

        assert lookup_url_kwarg in self.request.path_kwargs

        model_field = getattr(self.get_model(), self.lookup_field)
        obj = self.get_queryset().filter(getattr(model_field, '__eq__')(self.request.path_kwargs[lookup_url_kwarg])).first()

        self.check_object_permissions(obj)

        queryset = self.filter_queryset(self.get_queryset())

        return JSONResponse(get_model_siblings(self.model, obj, queryset))
