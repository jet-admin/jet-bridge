import re

import graphene
from jet_bridge_base.filters import lookups
from jet_bridge_base.filters.filter_for_dbfield import filter_for_data_type
from jet_bridge_base.filters.model_search import get_model_search_filter, search_queryset
from jet_bridge_base.serializers.model import get_model_serializer
from jet_bridge_base.serializers.model_serializer import get_column_data_type
from sqlalchemy import inspect, desc, column as sqlcolumn

from jet_bridge_base.db import get_mapped_base
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.utils.queryset import queryset_count_optimized
from jet_bridge_base.views.base.api import APIView


class RawScalar(graphene.Scalar):
    @staticmethod
    def serialize(value):
        return value

    @staticmethod
    def parse_literal(node, _variables=None):
        return node.value

    @staticmethod
    def parse_value(value):
        return value


class PaginationType(graphene.InputObjectType):
    page = graphene.Int()
    offset = graphene.Int()
    limit = graphene.Int()


class SearchType(graphene.InputObjectType):
    query = graphene.String()


class PaginationResponseType(graphene.ObjectType):
    count = graphene.Int()
    limit = graphene.Int()
    offset = graphene.Int(required=False)
    page = graphene.Int(required=False)
    hasMore = graphene.Boolean(required=False)


def clean_name(name):
    name = re.sub(r'[^_a-zA-Z0-9]', r'_', name)
    name = re.sub(r'^(\d)', r'_\1', name)
    return name


def clean_keys(obj):
    pairs = map(lambda x: [clean_name(x[0]), x[1]], obj.items())
    return dict(pairs)


class GraphQLView(APIView):
    # serializer_class = ModelDescriptionSerializer
    # permission_classes = (HasProjectPermissions,)
    model_filters_types = {}
    model_columns_filters_types = {}

    def get_queryset(self, request, Model, only_columns=None):
        if only_columns:
            queryset = request.session.query(*only_columns)
        else:
            queryset = request.session.query(Model)

        mapper = inspect(Model)
        auto_pk = getattr(mapper.tables[0], '__jet_auto_pk__', False) if len(mapper.tables) else None
        if auto_pk:
            queryset = queryset.filter(mapper.primary_key[0].isnot(None))

        return queryset

    def filter_queryset(self, MappedBase, queryset, mapper, filters, relationship=None):
        columns = dict(map(lambda x: (x.key, x), mapper.columns))

        for filters_item in filters:
            for filter_name, filter_lookups in filters_item.items():
                column = columns.get(filter_name)

                if column is None:
                    continue

                for lookup_name, lookup_value in filter_lookups.items():
                    if lookup_name == 'relation':
                        foreign_key = next(iter(column.foreign_keys))
                        relationship = None

                        for relation in mapper.relationships.values():
                            if len(relation.local_columns) != 1:
                                continue
                            local_column = next(iter(relation.local_columns))
                            if local_column is None:
                                continue
                            if local_column.name != column.name:
                                continue
                            relationship = relation.class_attribute
                            break

                        if relationship:
                            relation_mapper = None

                            for cls in MappedBase.classes:
                                cls_mapper = inspect(cls)
                                if cls_mapper.tables[0] == foreign_key.column.table:
                                    relation_mapper = cls_mapper
                                    break

                            if relation_mapper:
                                queryset = self.filter_queryset(MappedBase, queryset, relation_mapper, lookup_value, relationship)
                    else:
                        item = filter_for_data_type(column.type)
                        lookup = lookups.by_gql.get(lookup_name)
                        instance = item['filter_class'](
                            name=column.key,
                            column=column,
                            lookup=lookup,
                            exclude=False
                        )
                        criterion = instance.get_loookup_criterion(lookup_value)

                        if relationship:
                            queryset = queryset.filter(relationship.has(criterion))
                        else:
                            queryset = queryset.filter(criterion)

        return queryset

    def search_queryset(self, queryset, mapper, search):
        if search is not None:
            query = search['query']
            queryset = search_queryset(queryset, mapper, query)

        return queryset

    def sort_queryset(self, queryset, sort):
        def map_order_field(sorting):
            parts = sorting.split(':', 1)

            if len(parts) == 2:
                name = parts[0]
                descending = parts[1] == 'desc'
            else:
                name = parts[0]
                descending = False

            field = sqlcolumn(name)
            if descending:
                field = desc(field)
            return field

        if len(sort):
            order_by = list(map(lambda x: map_order_field(x), sort))
            queryset = queryset.order_by(*order_by)

        return queryset

    def get_pagination_limit(self, pagination):
        return pagination.get('limit', 20)

    def paginate_queryset(self, queryset, pagination):
        limit = self.get_pagination_limit(pagination)

        if 'offset' in pagination:
            queryset = queryset.offset(pagination['offset'])
        elif 'page' in pagination:
            queryset = queryset.offset((pagination['page'] - 1) * limit)

        queryset = queryset.limit(limit)

        return queryset

    def get_model_filters_type(self, mapper, depth=1):
        attrs = {}
        with_relations = depth <= 4

        for column in mapper.columns:
            column_filters_type = self.get_model_field_filters_type(mapper, column, with_relations, depth)
            attr_name = clean_name(column.name)
            attrs[attr_name] = column_filters_type()

        model_name = clean_name(mapper.selectable.name)
        name = 'Model{}Depth{}NestedFiltersType'.format(model_name, depth) if with_relations \
            else 'Model{}Depth{}FiltersType'.format(model_name, depth)

        if name in self.model_filters_types:
            return graphene.List(self.model_filters_types[name])

        cls = type(name, (graphene.InputObjectType,), attrs)
        self.model_filters_types[name] = cls
        return graphene.List(cls)

    def get_model_field_filters_type(self, mapper, column, with_relations, depth=1):
        item = filter_for_data_type(column.type)

        attrs = {}

        for lookup in item['lookups']:
            gql_lookup = lookups.gql.get(lookup)
            attrs[gql_lookup] = RawScalar()

        if with_relations and column.foreign_keys:
            foreign_key = next(iter(column.foreign_keys))
            table = foreign_key.column.table

            column_filters_type = self.get_model_filters_type(table, depth + 1)
            attrs['relation'] = column_filters_type

        model_name = clean_name(mapper.selectable.name)
        column_name = clean_name(column.name)
        name = 'Model{}Column{}Depth{}NestedFiltersType'.format(model_name, column_name, depth) if with_relations \
            else 'Model{}Column{}Depth{}FiltersType'.format(model_name, column_name, depth)

        if name in self.model_columns_filters_types:
            return self.model_columns_filters_types[name]

        cls = type(name, (graphene.InputObjectType,), attrs)
        self.model_columns_filters_types[name] = cls
        return cls

    def get_model_attrs_type(self, mapper):
        name = clean_name(mapper.selectable.name)
        attrs = {}

        for column in mapper.columns:
            attr_name = clean_name(column.name)
            attrs[attr_name] = RawScalar()

        return type('Model{}RecordAttrsType'.format(name), (graphene.ObjectType,), attrs)

    def get_selections(self, info, path):
        i = 0
        current_field = info.field_asts[0]

        for path_item in path:
            for selection in current_field.selection_set.selections:
                if selection.name.value == path_item:
                    if i == len(path) - 1:
                        return selection.selection_set.selections
                    else:
                        current_field = selection
                        break

            i += 1

    def get_query_type(self, request):
        MappedBase = get_mapped_base(request)

        query_attrs = {}

        for Model in MappedBase.classes:
            mapper = inspect(Model)
            name = clean_name(mapper.selectable.name)

            FiltersType = self.get_model_filters_type(mapper)
            ModelAttrsType = self.get_model_attrs_type(mapper)
            ModelType = type('Model{}ModelType'.format(name), (graphene.ObjectType,), {
                'attrs': graphene.Field(ModelAttrsType),
                'allAttrs': graphene.Field(RawScalar)
            })
            ModelListType = type('Model{}ModelListType'.format(name), (graphene.ObjectType,), {
                'data': graphene.List(ModelType),
                'pagination': graphene.Field(PaginationResponseType)
            })

            def create_list_resolver(Model, mapper):
                def resolver(parent, info, filters=None, sort=None, pagination=None, search=None):
                    try:
                        filters = filters or []
                        sort = sort or []
                        pagination = pagination or {}

                        field_selections = self.get_selections(info, ['data', 'attrs']) or []
                        field_names = list(map(lambda x: x.name.value, field_selections))
                        data_selections = self.get_selections(info, ['data']) or []
                        data_names = list(map(lambda x: x.name.value, data_selections))
                        model_attrs = dict(map(lambda x: [clean_name(x), getattr(Model, x)], dir(Model)))
                        only_columns = list(map(lambda x: model_attrs.get(x), field_names)) \
                            if len(field_names) and 'allAttrs' not in data_names else None

                        queryset = self.get_queryset(request, Model, only_columns)

                        queryset = self.filter_queryset(MappedBase, queryset, mapper, filters)
                        queryset = self.search_queryset(queryset, mapper, search)
                        queryset = self.sort_queryset(queryset, sort)

                        queryset_page = self.paginate_queryset(queryset, pagination)

                        serializer_class = get_model_serializer(Model)
                        serializer_context = {}
                        queryset_page_serialized = list(map(lambda x: clean_keys(serializer_class(
                            instance=x,
                            context=serializer_context
                        ).representation_data), queryset_page))

                        result = {
                            'data': list(map(lambda x: {
                                'attrs': x,
                                'allAttrs': x
                            }, queryset_page_serialized))
                        }

                        pagination_selections = self.get_selections(info, ['pagination']) or []
                        pagination_names = list(map(lambda x: x.name.value, pagination_selections))

                        if len(pagination_names):
                            limit = self.get_pagination_limit(pagination)
                            offset = pagination.get('offset')
                            page = pagination.get('page')

                            result['pagination'] = {
                                'limit': limit,
                                'offset': offset,
                                'page': page
                            }

                            if 'count' in pagination_names or 'hasMore' in pagination_names:
                                count = queryset_count_optimized(request, queryset)
                                result['pagination']['count'] = count

                                if offset is not None:
                                    result['pagination']['hasMore'] = offset + limit < count
                                elif page is not None:
                                    result['pagination']['hasMore'] = page * limit < count

                        return result
                    except Exception as e:
                        raise e
                return resolver

            query_attrs[name] = graphene.Field(
                ModelListType,
                filters=FiltersType,
                sort=graphene.List(graphene.String),
                pagination=PaginationType(),
                search=SearchType()
            )
            query_attrs['resolve_{}'.format(name)] = create_list_resolver(Model, mapper)

        return type('Query', (graphene.ObjectType,), query_attrs)

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        Query = self.get_query_type(request)

        schema = graphene.Schema(query=Query, auto_camelcase=False)

        if 'query' not in request.data:
            return JSONResponse({})

        query = request.data.get('query')
        result = schema.execute(query, variables={}, context_value={'session': request.session})

        if result.errors is not None:
            return JSONResponse({'errors': map(lambda x: x.message, result.errors)})

        return JSONResponse({
            'data': result.data
        })
