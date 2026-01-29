from jet_bridge_base import status, fields
from jet_bridge_base.exceptions.missing_argument_error import MissingArgumentError
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.utils.exceptions import serialize_validation_error
from jet_bridge_base.views.model_description import inspect_uniform
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Row

from jet_bridge_base.db import get_mapped_base
from jet_bridge_base.db_types import apply_default_ordering
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
from jet_bridge_base.utils.siblings import get_model_siblings
from jet_bridge_base.views.mixins.model import ModelAPIViewMixin


class ModelViewSet(ModelAPIViewMixin):
    permission_classes = (HasProjectPermissions, ReadOnly)
    track_queries = True

    def before_dispatch(self, request):
        super(ModelViewSet, self).before_dispatch(request)

    def on_finish(self):
        super(ModelViewSet, self).on_finish()

    def required_project_permission(self, request):
        model_name = self.get_model_name(request)
        return {
            'permission_type': 'model',
            'permission_object': model_name,
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

    def get_model_name(self, request):
        return request.path_kwargs['model']

    def get_model(self, request):
        model_name = self.get_model_name(request)
        MappedBase = get_mapped_base(request)

        if model_name not in MappedBase.classes:
            raise NotFound

        return MappedBase.classes[model_name]

    def get_model_lookup_field(self, request):
        mapper = inspect_uniform(self.get_model(request))
        return mapper.primary_key[0].name

    def get_serializer_class(self, request):
        Model = self.get_model(request)
        return get_model_serializer(Model)

    def get_filter_class(self, request):
        Model = self.get_model(request)
        return get_model_filter_class(request, Model)

    def get_queryset(self, request):
        Model = self.get_model(request)
        queryset = request.session.query(Model)

        mapper = inspect_uniform(Model)
        auto_pk = getattr(mapper.tables[0], '__jet_auto_pk__', False) if len(mapper.tables) else None
        if auto_pk:
            queryset = queryset.filter(mapper.primary_key[0].isnot(None))

        return queryset

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

        self.apply_timezone(request)
        request.apply_rls_if_enabled()

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
        self.apply_timezone(request)
        request.apply_rls_if_enabled()

        queryset = self.filter_queryset(request, self.get_queryset(request))

        lookup_field = self.get_model_lookup_field(request)
        y_func = request.get_argument('_y_func').lower()
        y_column = request.get_argument('_y_column', lookup_field)

        model_name = self.get_model_name(request)
        model_serializer = self.get_serializer(request)

        if y_func == 'count':
            y_serializer = fields.IntegerField()
        else:
            y_serializers = list(filter(lambda x: x.field_name == y_column, model_serializer.fields))

            if len(y_serializers) == 0:
                raise ValidationError('Table "{}" does not have column "{}"'.format(model_name, y_column))

            y_serializer = y_serializers[0]

        filter_instance = ModelAggregateFilter()
        filter_instance.model = self.get_model(request)

        try:
            data = filter_instance.filter(queryset, {
                'y_func': y_func,
                'y_column': y_column
            })
        except SQLAlchemyError:
            queryset.session.rollback()
            raise

        if y_func in ['count', 'sum', 'avg'] and data is None:
            data = 0

        result = y_serializer.to_representation(data)  # TODO: Refactor serializer

        return JSONResponse({
            'y_func': result
        })

    @action(methods=['get'], detail=False)
    def group(self, request, *args, **kwargs):
        self.apply_timezone(request)
        request.apply_rls_if_enabled()

        queryset = self.filter_queryset(request, self.get_queryset(request))

        lookup_field = self.get_model_lookup_field(request)
        x_columns = request.get_arguments('_x_column')
        x_lookup_names = request.get_arguments('_x_lookup', None)
        y_func = request.get_argument('_y_func').lower()
        y_column = request.get_argument('_y_column', lookup_field)

        try:
            page_size = int(request.get_argument('_per_page'))
            page_size = max(page_size, 1)
            page_size = min(page_size, 100000)
        except (MissingArgumentError, ValueError):
            page_size = 10000

        # model_serializer = self.get_serializer(request)

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
        }).limit(page_size)

        def map_item(row):
            if isinstance(row, Row):
                row = dict(row)

            if isinstance(row, dict):
                if y_func in ['count', 'sum', 'avg'] and 'y_func' in row and row['y_func'] is None:
                    row['y_func'] = 0

                if 'group_1' in row:
                    row['group'] = row['group_1']
                    del row['group_1']

                return row
            else:
                return row

        try:
            instance = list(map(lambda x: map_item(x), queryset))
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
        self.apply_timezone(request)
        request.apply_rls_if_enabled()

        queryset = self.filter_queryset(request, self.get_queryset(request))
        Model = self.get_model(request)
        ReorderSerializer = get_reorder_serializer(Model, queryset, request.session)

        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return JSONResponse(serializer.representation_data)

    @action(methods=['post'], detail=False)
    def reset_order(self, request, *args, **kwargs):
        self.apply_timezone(request)
        request.apply_rls_if_enabled()

        queryset = self.filter_queryset(request, self.get_queryset(request))
        Model = self.get_model(request)
        ResetOrderSerializer = get_reset_order_serializer(Model, queryset, request.session)

        serializer = ResetOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return JSONResponse(serializer.representation_data)

    @action(methods=['get'], detail=True)
    def get_siblings(self, request, *args, **kwargs):
        self.apply_timezone(request)
        request.apply_rls_if_enabled()

        queryset = self.filter_queryset(request, self.get_queryset(request))
        obj = self.get_object(request)
        Model = self.get_model(request)
        result = get_model_siblings(request, Model, obj, queryset)

        return JSONResponse(result)
