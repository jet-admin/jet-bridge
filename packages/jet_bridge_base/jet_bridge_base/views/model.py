from jet_bridge_base import status
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.utils.exceptions import serialize_validation_error
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

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
    permission_classes = (HasProjectPermissions, ReadOnly)

    def before_dispatch(self, request):
        super(ModelViewSet, self).before_dispatch(request)
        mapper = inspect(self.get_model(request))
        self.lookup_field = mapper.primary_key[0].name

    def on_finish(self):
        super(ModelViewSet, self).on_finish()

    def required_project_permission(self, request):
        return {
            'permission_type': 'model',
            'permission_object': request.path_kwargs['model'],
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
            }.get(request.action, 'w')
        }

    def get_model(self, request):
        MappedBase = get_mapped_base(request)

        if request.path_kwargs['model'] not in MappedBase.classes:
            raise NotFound

        return MappedBase.classes[request.path_kwargs['model']]

    def get_serializer_class(self, request):
        Model = self.get_model(request)
        return get_model_serializer(Model)

    def get_filter_class(self, request):
        Model = self.get_model(request)
        return get_model_filter_class(request, Model)

    def get_queryset(self, request):
        Model = self.get_model(request)

        return request.session.query(Model)

    def filter_queryset(self, request, queryset):
        queryset = super(ModelViewSet, self).filter_queryset(request, queryset)
        if request.action == 'list':
            Model = self.get_model(request)
            queryset = apply_default_ordering(Model, queryset)
        return queryset

    @action(methods=['post'], detail=False)
    def bulk_create(self, request, *args, **kwargs):
        if not isinstance(request.data, list):
            return JSONResponse({'error': 'Request body should be an array'}, status=status.HTTP_400_BAD_REQUEST)

        result = []

        for item in request.data:
            serializer = self.get_serializer(request, data=item)

            try:
                serializer.is_valid(raise_exception=True)
                self.perform_create(request, serializer)
                result.append({'success': True})
            except ValidationError as e:
                result.append({'success': False, 'errors': serialize_validation_error(e)})
            except Exception as e:
                result.append({'success': False, 'errors': {'non_field_errors': str(e)}})

        return JSONResponse(result, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False)
    def aggregate(self, request, *args, **kwargs):
        queryset = self.filter_queryset(request, self.get_queryset(request))

        y_func = request.get_argument('_y_func').lower()
        y_column = request.get_argument('_y_column', self.lookup_field)

        model_serializer = self.get_serializer(request)

        y_serializers = list(filter(lambda x: x.field_name == y_column, model_serializer.fields))
        y_serializer = y_serializers[0]

        filter_instance = ModelAggregateFilter()
        filter_instance.model = self.get_model(request)

        try:
            queryset = filter_instance.filter(queryset, {
                'y_func': y_func,
                'y_column': y_column
            }).one()
        except SQLAlchemyError:
            queryset.session.rollback()
            raise

        result = y_serializer.to_representation(queryset[0])  # TODO: Refactor serializer

        return JSONResponse({
            'y_func': result
        })

    @action(methods=['get'], detail=False)
    def group(self, request, *args, **kwargs):
        queryset = self.filter_queryset(request, self.get_queryset(request))

        x_columns = request.get_arguments('_x_column')
        x_lookup_names = request.get_arguments('_x_lookup', None)
        y_func = request.get_argument('_y_func').lower()
        y_column = request.get_argument('_y_column', self.lookup_field)

        model_serializer = self.get_serializer(request)

        # x_serializers = list(filter(lambda x: x.field_name == x_column, model_serializer.fields))
        # x_serializer = x_serializers[0]

        # y_serializers = list(filter(lambda x: x.field_name == y_column, model_serializer.fields))
        # y_serializer = y_serializers[0]

        filter_instance = ModelGroupFilter()
        filter_instance.model = self.get_model(request)
        queryset = filter_instance.filter(queryset, {
            'x_columns': x_columns,
            'x_lookups': x_lookup_names,
            'y_func': y_func,
            'y_column': y_column
        })

        try:
            instance = list(queryset)
        except SQLAlchemyError:
            queryset.session.rollback()
            raise

        return JSONResponse(instance)
        # serializer = ModelGroupSerializer(
        #     instance=instance,
        #     many=True,
        #     # TODO: Refactor serializer
        #     # group_serializer=x_serializer,
        #     # y_func_serializer=y_serializer
        # )
        #
        # return JSONResponse(serializer.representation_data)

    @action(methods=['post'], detail=False)
    def reorder(self, request, *args, **kwargs):
        queryset = self.filter_queryset(request, self.get_queryset(request))
        Model = self.get_model(request)
        ReorderSerializer = get_reorder_serializer(Model, queryset, request.session)

        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return JSONResponse(serializer.representation_data)

    @action(methods=['post'], detail=False)
    def reset_order(self, request, *args, **kwargs):
        queryset = self.filter_queryset(request, self.get_queryset(request))
        Model = self.get_model(request)
        ResetOrderSerializer = get_reset_order_serializer(Model, queryset, request.session)

        serializer = ResetOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return JSONResponse(serializer.representation_data)

    @action(methods=['get'], detail=True)
    def get_siblings(self, request, *args, **kwargs):
        queryset = self.filter_queryset(request, self.get_queryset(request))
        obj = self.get_object(request)
        Model = self.get_model(request)
        result = get_model_siblings(request, Model, obj, queryset)

        return JSONResponse(result)
