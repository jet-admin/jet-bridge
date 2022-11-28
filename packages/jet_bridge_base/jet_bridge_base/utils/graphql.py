import re
import graphene
from jet_bridge_base.models.model_relation_override import ModelRelationOverrideModel
from jet_bridge_base.store import store
from jet_bridge_base.utils.relations import parse_relationship_direction
from sqlalchemy import inspect, desc, MetaData
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import MANYTOONE, ONETOMANY, aliased

from jet_bridge_base.db import get_mapped_base, get_engine, load_mapped_base, get_request_connection
from jet_bridge_base.filters import lookups
from jet_bridge_base.filters.filter_for_dbfield import filter_for_data_type
from jet_bridge_base.filters.model_group import get_query_func_by_name
from jet_bridge_base.filters.model_search import search_queryset
from jet_bridge_base.serializers.model import get_model_serializer
from jet_bridge_base.utils.common import get_set_first, any_type_sorter
from jet_bridge_base.utils.gql import RawScalar
from jet_bridge_base.utils.queryset import queryset_count_optimized, apply_default_ordering


class FieldSortType(graphene.InputObjectType):
    descending = graphene.Boolean(required=False)


class PaginationType(graphene.InputObjectType):
    page = graphene.Int()
    offset = graphene.Int()
    limit = graphene.Int()


class SearchType(graphene.InputObjectType):
    query = graphene.String()


class AggregateFuncType(graphene.Enum):
    Count = 'count'
    Sum = 'sum'
    Min = 'min'
    Max = 'max'
    Avg = 'avg'


class AggregateType(graphene.InputObjectType):
    func = AggregateFuncType()
    attr = graphene.String(required=False)


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


class GraphQLSchemaGenerator(object):
    def __init__(self):
        self.relationships_by_name = dict()
        self.relationships_by_clean_name = dict()
        self.model_filters_types = dict()
        self.model_filters_field_types = dict()
        self.model_filters_relationship_types = dict()
        self.model_lookups_types = dict()
        self.model_lookups_field_types = dict()
        self.model_lookups_relationship_types = dict()
        self.model_sort_types = dict()

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

    def get_relationships(self, request, MappedBase, draft):
        result = {}
        relationships_overrides = {}

        if store.is_ok():
            connection = get_request_connection(request)

            with store.session() as session:
                overrides = session.query(ModelRelationOverrideModel).filter(
                    ModelRelationOverrideModel.connection_id == connection['id'],
                    draft == draft
                ).all()

                for override in overrides:
                    if override.model not in relationships_overrides:
                        relationships_overrides[override.model] = []
                    relationships_overrides[override.model].append(override)

        for Model in MappedBase.classes:
            model_relationships = {}

            mapper = inspect(Model)
            name = mapper.selectable.name

            for relationship in mapper.relationships.values():
                local_column = get_set_first(relationship.local_columns)
                relation_column = get_set_first(relationship.remote_side)

                if relationship.direction == MANYTOONE:
                    related_name = relationship.mapper.selectable.name
                    related_model = MappedBase.classes.get(related_name)

                    model_relationships[relationship.key] = {
                        'name': relationship.key,
                        'direction': relationship.direction,
                        'local_column': local_column,
                        'local_column_name': local_column.name if local_column is not None else None,
                        'related_model': related_model,
                        'related_mapper': relationship.mapper,
                        'related_column': relation_column,
                        'related_column_name': relation_column.name if relation_column is not None else None
                    }
                elif relationship.direction == ONETOMANY:
                    related_name = relationship.mapper.selectable.name
                    related_model = MappedBase.classes.get(related_name)

                    model_relationships[relationship.key] = {
                        'name': relationship.key,
                        'direction': relationship.direction,
                        'local_column': local_column,
                        'local_column_name': local_column.name if local_column is not None else None,
                        'related_model': related_model,
                        'related_mapper': relationship.mapper,
                        'related_column': relation_column,
                        'related_column_name': relation_column.name if relation_column is not None else None
                    }

            model_relationships_overrides = relationships_overrides.get(name, [])

            for override in model_relationships_overrides:
                direction = parse_relationship_direction(override.direction)
                local_column = getattr(Model, override.local_field)
                related_name = override.related_model
                related_model = MappedBase.classes.get(related_name)

                if not related_model and '.' in related_name:
                    schema, table = related_name.split('.', 1)
                    engine = get_engine(request)
                    bind = MappedBase.metadata.bind

                    related_metadata = MetaData(schema=schema, bind=bind)
                    related_metadata.reflect(bind=engine, schema=schema, only=[table])
                    related_base = automap_base(metadata=related_metadata)
                    load_mapped_base(related_base)

                    related_model = related_base.classes.get(table)

                if not related_model:
                    continue

                related_mapper = inspect(related_model)
                related_column = getattr(related_model, override.related_field)

                model_relationships[override.name] = {
                    'name': override.name,
                    'direction': direction,
                    'local_column': local_column,
                    'local_column_name': override.local_field,
                    'related_model': related_model,
                    'related_mapper': related_mapper,
                    'related_column': related_column,
                    'related_column_name': override.related_field
                }

            result[name] = model_relationships

        return result

    def clean_relationships_by_name(self, relationships):
        def map_model_relations(x):
            return clean_name(x[0]), x[1]

        def map_models(x):
            return x[0], dict(map(lambda r: map_model_relations(r), x[1].items()))

        return dict(map(lambda x: map_models(x), relationships.items()))

    def get_model_columns_by_clean_name(self, mapper):
        return dict(map(lambda x: (clean_name(x[0]), x[1]), mapper.columns.items()))

    def get_model_relationships(self, mapper):
        name = mapper.selectable.name
        return self.relationships_by_name.get(name, {}).values()

    def get_model_relationships_by_name(self, mapper):
        name = mapper.selectable.name
        return self.relationships_by_name.get(name, {})

    def get_model_relationships_by_clean_name(self, mapper):
        name = mapper.selectable.name
        return self.relationships_by_clean_name.get(name, {})

    def filter_queryset(self, MappedBase, queryset, mapper, filters, parent_relations=None, exclude=False):
        parent_relations = parent_relations or []

        for filters_item in filters:
            for filter_name, filter_lookups in filters_item.items():
                if filter_name == '_not_':
                    queryset = self.filter_queryset(
                        MappedBase,
                        queryset,
                        mapper,
                        filter_lookups,
                        parent_relations,
                        exclude=True
                    )
                    continue

                columns_by_clean_name = self.get_model_columns_by_clean_name(mapper)
                column = columns_by_clean_name.get(filter_name)
                filter_relationship = self.get_model_relationships_by_clean_name(mapper).get(filter_name)

                if filter_relationship is not None:
                    for lookup_name, lookup_value in filter_lookups.items():
                        if lookup_name == 'relation':
                            relation_mapper = filter_relationship['related_mapper']
                            queryset = self.filter_queryset(
                                MappedBase,
                                queryset,
                                relation_mapper,
                                lookup_value,
                                [*parent_relations, filter_relationship],
                                exclude
                            )
                elif column is not None:
                    for lookup_name, lookup_value in filter_lookups.items():
                        if lookup_name == 'relation':
                            for relationship in self.get_model_relationships(mapper):
                                if relationship['direction'] != MANYTOONE or relationship['local_column_name'] != column.name:
                                    continue

                                relation_mapper = relationship['related_mapper']
                                queryset = self.filter_queryset(
                                    MappedBase,
                                    queryset,
                                    relation_mapper,
                                    lookup_value,
                                    [*parent_relations, relationship],
                                    exclude
                                )
                                break
                        else:
                            if len(parent_relations):
                                last_related_model = None

                                for relationship in parent_relations:
                                    related_model = aliased(relationship['related_model'])
                                    related_column = getattr(related_model, relationship['related_column'].name)
                                    local_column = getattr(last_related_model, relationship['local_column'].name) if last_related_model else relationship['local_column']
                                    queryset = queryset.join(
                                        related_model,
                                        related_column == local_column
                                    )
                                    last_related_model = related_model

                                column = getattr(last_related_model, column.name)

                            item = filter_for_data_type(column.type)
                            lookup = lookups.by_gql.get(lookup_name)
                            instance = item['filter_class'](
                                name=column.key,
                                column=column,
                                lookup=lookup,
                                exclude=False
                            )
                            criterion = instance.get_loookup_criterion(lookup_value)
                            criterion = ~criterion if exclude else criterion

                            queryset = queryset.filter(criterion)

        return queryset

    def search_queryset(self, queryset, mapper, search):
        if search is not None:
            query = search['query']
            queryset = search_queryset(queryset, mapper, query)

        return queryset

    def get_models_lookups(self, request, MappedBase, models, Model, mapper, lookups):
        result = []

        for lookup_item in lookups:
            lookup_result = self.get_models_lookup(
                lookup_item,
                request,
                MappedBase,
                models,
                Model,
                mapper
            )
            result.append(lookup_result)

        return result

    def get_models_lookup(self, lookup_item, request, MappedBase, models, Model, mapper):
        result = {}

        for lookup_name, lookup_data in lookup_item.items():
            columns_by_clean_name = self.get_model_columns_by_clean_name(mapper)
            column = columns_by_clean_name.get(lookup_name)
            relationship = self.get_model_relationships_by_clean_name(mapper).get(lookup_name)

            if relationship is not None:
                lookup_result = {}
                local_column = relationship['local_column']
                lookup_values = sorted(set(map(lambda x: getattr(x, local_column.name), models)), key=any_type_sorter)

                lookup_result['return'] = lookup_data.get('return', False)
                lookup_result['return_list'] = lookup_data.get('returnList', False)
                lookup_result['Model'] = Model
                lookup_result['mapper'] = mapper
                lookup_result['model_values'] = list(map(lambda x: {'instance': x, 'value': getattr(x, local_column.name)}, models))
                lookup_result['source_column'] = local_column.name

                if 'aggregate' in lookup_data:
                    relation_model = relationship['related_model']
                    relation_mapper = relationship['related_mapper']
                    relation_column = relationship['related_column']

                    if 'attr' in lookup_data['aggregate']:
                        aggregate_column_name = lookup_data['aggregate']['attr']
                    else:
                        aggregate_column_name = relation_mapper.primary_key[0].name

                    aggregate_column = getattr(relation_model, aggregate_column_name)
                    aggregate_func = get_query_func_by_name(lookup_data['aggregate']['func'], aggregate_column)

                    groups = request.session\
                        .query(relation_column, aggregate_func)\
                        .filter(relation_column.in_(lookup_values))\
                        .group_by(relation_column)
                    groups_dict = dict(groups)

                    lookup_result['aggregated_values'] = list(map(lambda x: {
                        'instance': x,
                        'value': groups_dict.get(getattr(x, local_column.name), 0)
                    }, models))
                    lookup_result['related_column'] = relation_column.name

                if 'relation' in lookup_data:
                    relation_model = relationship['related_model']
                    relation_mapper = relationship['related_mapper']
                    relation_column = relationship['related_column']

                    related_models = request.session\
                        .query(relation_model)\
                        .filter(relation_column.in_(lookup_values))\
                        .all()
                    related_models = list(related_models)

                    lookup_result['related'] = self.get_models_lookup(
                        lookup_data['relation'],
                        request,
                        MappedBase,
                        related_models,
                        relation_model,
                        relation_mapper
                    )
                    lookup_result['related_column'] = relation_column.name

                result[lookup_name] = lookup_result
            elif column is not None:
                lookup_result = {}
                lookup_values = sorted(set(map(lambda x: getattr(x, column.name), models)), key=any_type_sorter)

                lookup_result['return'] = lookup_data.get('return', False)
                lookup_result['return_list'] = lookup_data.get('returnList', False)
                lookup_result['Model'] = Model
                lookup_result['mapper'] = mapper
                lookup_result['model_values'] = list(map(lambda x: {'instance': x, 'value': getattr(x, column.name)}, models))
                lookup_result['source_column'] = column.name

                if 'relation' in lookup_data:
                    for relationship in self.get_model_relationships(mapper):
                        if relationship['direction'] != MANYTOONE or relationship['local_column_name'] != column.name:
                            continue

                        relation_mapper = relationship['related_mapper']
                        relation_model = relationship['related_model']
                        relation_column = relationship['related_column']

                        related_models = request.session\
                            .query(relation_model)\
                            .filter(relation_column.in_(lookup_values))\
                            .all()
                        related_models = list(related_models)

                        lookup_result['related'] = self.get_models_lookup(
                            lookup_data['relation'],
                            request,
                            MappedBase,
                            related_models,
                            relation_model,
                            relation_mapper
                        )
                        lookup_result['related_column'] = relation_column.name
                        break

                result[lookup_name] = lookup_result

        return result

    def filter_lookup_models(self, lookup, instance_predicate=None):
        result = {}

        for lookup_name, lookup_data in lookup.items():
            item_result = {}

            model_values = lookup_data['model_values']

            if instance_predicate:
                model_values = list(filter(lambda x: instance_predicate(x['instance']), model_values))

            values = list(map(lambda x: x['value'], model_values))

            if lookup_data['return']:
                if lookup_data['return_list']:
                    item_result['value'] = values
                else:
                    item_result['value'] = values[0] if len(values) else None

            if 'related' in lookup_data:
                item_result['related'] = self.filter_lookup_models(
                    lookup_data['related'],
                    lambda x: getattr(x, lookup_data['related_column']) in values
                )

            if 'aggregated_values' in lookup_data:
                model_values = list(filter(
                    lambda x: getattr(x['instance'], lookup_data['source_column']) in values,
                    lookup_data['aggregated_values']
                ))
                item_result['aggregated'] = model_values[0]['value'] if len(model_values) else 0

            result[lookup_name] = item_result

        return result

    def map_sort_order_field(self, mapper, name, options):
        descending = options.get('descending', False)

        columns_by_clean_name = self.get_model_columns_by_clean_name(mapper)
        column = columns_by_clean_name.get(name)

        if column is None:
            return

        if descending:
            column = desc(column)

        return column

    def sort_queryset(self, queryset, Model, mapper, sort):
        for item in sort:
            order_by = map(lambda x: self.map_sort_order_field(mapper, x[0], x[1]), item.items())
            order_by = filter(lambda x: x is not None, order_by)
            order_by = list(order_by)

            queryset = queryset.order_by(*order_by)

        queryset = apply_default_ordering(Model, queryset)

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

    def get_model_filters_type(self, MappedBase, mapper, depth=1):
        with_relations = depth <= 4
        model_name = clean_name(mapper.selectable.name)
        cls_name = 'Model{}Depth{}NestedFiltersType'.format(model_name, depth) if with_relations \
            else 'Model{}Depth{}FiltersType'.format(model_name, depth)

        if cls_name in self.model_filters_types:
            return graphene.List(self.model_filters_types[cls_name])

        attrs = {}

        for column in mapper.columns:
            column_filters_type = self.get_model_field_filters_type(MappedBase, mapper, column, with_relations, depth)
            attr_name = clean_name(column.name)
            attrs[attr_name] = column_filters_type()

        if with_relations:
            for relationship in self.get_model_relationships(mapper):
                if relationship['direction'] != ONETOMANY:
                    continue

                relationship_filters_type = self.get_model_relationship_filters_type(MappedBase, mapper, relationship, with_relations, depth)
                attr_name = clean_name(relationship['name'])
                attrs[attr_name] = relationship_filters_type()

            attrs['_not_'] = self.get_model_filters_type(MappedBase, mapper, depth + 1)

        cls = type(cls_name, (graphene.InputObjectType,), attrs)
        self.model_filters_types[cls_name] = cls
        return graphene.List(cls)

    def get_model_field_filters_type(self, MappedBase, mapper, column, with_relations, depth=1):
        model_name = clean_name(mapper.selectable.name)
        column_name = clean_name(column.name)
        cls_name = 'Model{}Column{}Depth{}NestedFiltersType'.format(model_name, column_name, depth) if with_relations \
            else 'Model{}Column{}Depth{}FiltersType'.format(model_name, column_name, depth)

        if cls_name in self.model_filters_field_types:
            return self.model_filters_field_types[cls_name]

        attrs = {}
        item = filter_for_data_type(column.type)

        for lookup in item['lookups']:
            gql_lookup = lookups.gql.get(lookup)
            gql_scalar = lookups.gql_scalar.get(lookup, RawScalar())
            attrs[gql_lookup] = gql_scalar

        if with_relations:
            for relationship in self.get_model_relationships(mapper):
                if relationship['direction'] != MANYTOONE or relationship['local_column_name'] != column_name:
                    continue

                relation_mapper = relationship['related_mapper']
                column_filters_type = self.get_model_filters_type(MappedBase, relation_mapper, depth + 1)
                attrs['relation'] = column_filters_type
                break

        cls = type(cls_name, (graphene.InputObjectType,), attrs)
        self.model_filters_field_types[cls_name] = cls
        return cls

    def get_model_relationship_filters_type(self, MappedBase, mapper, relationship, with_relations, depth=1):
        model_name = clean_name(mapper.selectable.name)
        relationship_key = clean_name(relationship['name'])
        cls_name = 'Model{}Column{}Depth{}NestedRelationshipType'.format(model_name, relationship_key, depth) if with_relations \
            else 'Model{}Column{}Depth{}RelationshipType'.format(model_name, relationship_key, depth)

        if cls_name in self.model_filters_relationship_types:
            return self.model_filters_relationship_types[cls_name]

        attrs = {}

        lookups_type = self.get_model_filters_type(MappedBase, relationship['related_mapper'], depth + 1)
        attrs['relation'] = lookups_type

        cls = type(cls_name, (graphene.InputObjectType,), attrs)
        self.model_filters_relationship_types[cls_name] = cls
        return cls

    def get_model_lookups_type(self, MappedBase, mapper, depth=1):
        with_relations = depth <= 4
        model_name = clean_name(mapper.selectable.name)
        cls_name = 'Model{}Depth{}NestedLookupsType'.format(model_name, depth) if with_relations \
            else 'Model{}Depth{}LookupsType'.format(model_name, depth)

        if cls_name in self.model_lookups_types:
            return self.model_lookups_types[cls_name]

        attrs = {}

        for column in mapper.columns:
            column_lookups_type = self.get_model_field_lookups_type(MappedBase, mapper, column, with_relations, depth)
            attr_name = clean_name(column.name)
            attrs[attr_name] = column_lookups_type()

        if with_relations:
            for relationship in self.get_model_relationships(mapper):
                if relationship['direction'] != ONETOMANY:
                    continue

                relationship_lookups_type = self.get_model_relationship_lookups_type(MappedBase, mapper, relationship, with_relations, depth)
                attr_name = clean_name(relationship['name'])
                attrs[attr_name] = relationship_lookups_type()

        cls = type(cls_name, (graphene.InputObjectType,), attrs)
        self.model_lookups_types[cls_name] = cls
        return cls

    def get_model_field_lookups_type(self, MappedBase, mapper, column, with_relations, depth=1):
        model_name = clean_name(mapper.selectable.name)
        column_name = clean_name(column.name)
        cls_name = 'Model{}Column{}Depth{}NestedLookupsFieldType'.format(model_name, column_name, depth) if with_relations \
            else 'Model{}Column{}Depth{}LookupsFieldType'.format(model_name, column_name, depth)

        if cls_name in self.model_lookups_field_types:
            return self.model_lookups_field_types[cls_name]

        attrs = {
            'return': graphene.Boolean(),
            'returnList': graphene.Boolean()
        }

        if with_relations:
            for relationship in self.get_model_relationships(mapper):
                if relationship['direction'] != MANYTOONE or relationship['local_column_name'] != column_name:
                    continue

                relation_mapper = relationship['related_mapper']
                lookups_type = self.get_model_lookups_type(MappedBase, relation_mapper, depth + 1)
                attrs['relation'] = lookups_type()
                break

        cls = type(cls_name, (graphene.InputObjectType,), attrs)
        self.model_lookups_field_types[cls_name] = cls
        return cls

    def get_model_relationship_lookups_type(self, MappedBase, mapper, relationship, with_relations, depth=1):
        model_name = clean_name(mapper.selectable.name)
        relationship_key = clean_name(relationship['name'])
        cls_name = 'Model{}Column{}Depth{}NestedLookupsRelationshipType'.format(model_name, relationship_key, depth) if with_relations \
            else 'Model{}Column{}Depth{}LookupsRelationshipType'.format(model_name, relationship_key, depth)

        if cls_name in self.model_lookups_relationship_types:
            return self.model_lookups_relationship_types[cls_name]

        attrs = {
            'aggregate': AggregateType()
        }

        lookups_type = self.get_model_lookups_type(MappedBase, relationship['related_mapper'], depth + 1)
        attrs['relation'] = lookups_type()

        cls = type(cls_name, (graphene.InputObjectType,), attrs)
        self.model_lookups_relationship_types[cls_name] = cls
        return cls

    def get_model_sort_type(self, mapper):
        model_name = clean_name(mapper.selectable.name)
        cls_name = 'Model{}SortType'.format(model_name)

        if cls_name in self.model_sort_types:
            return graphene.List(self.model_sort_types[cls_name])

        attrs = {}

        for column in mapper.columns:
            attr_name = clean_name(column.name)
            attrs[attr_name] = FieldSortType()

        cls = type(cls_name, (graphene.InputObjectType,), attrs)
        self.model_sort_types[cls_name] = cls
        return graphene.List(cls)

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

    def resolve_model_list(self, MappedBase, Model, mapper,info, filters=None, lookups=None, sort=None, pagination=None, search=None):
        try:
            filters = filters or []
            lookups = lookups or []
            sort = sort or []
            pagination = pagination or {}

            request = info.context.get('request')

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
            queryset = self.sort_queryset(queryset, Model, mapper, sort)

            queryset_page = list(self.paginate_queryset(queryset, pagination))

            serializer_class = get_model_serializer(Model)
            serializer_context = {}

            queryset_page_lookups = self.get_models_lookups(request, MappedBase, queryset_page, Model, mapper, lookups)

            def map_queryset_page_item(item):
                serialized = serializer_class(instance=item, context=serializer_context).representation_data
                serialized = clean_keys(serialized)

                return {
                    'attrs': serialized,
                    'allAttrs': serialized,
                    'lookups': list(map(
                        lambda x: self.filter_lookup_models(x, lambda instance: instance == item),
                        queryset_page_lookups
                    ))
                }

            result = {
                'data': list(map(map_queryset_page_item, queryset_page))
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

    def get_query_type(self, request, draft, before_resolve=None):
        MappedBase = get_mapped_base(request)

        query_attrs = {}

        self.relationships_by_name = self.get_relationships(request, MappedBase, draft)
        self.relationships_by_clean_name = self.clean_relationships_by_name(self.relationships_by_name)

        for Model in MappedBase.classes:
            mapper = inspect(Model)
            name = clean_name(mapper.selectable.name)

            FiltersType = self.get_model_filters_type(MappedBase, mapper)
            LookupsType = self.get_model_lookups_type(MappedBase, mapper)
            SortType = self.get_model_sort_type(mapper)
            ModelAttrsType = self.get_model_attrs_type(mapper)
            ModelType = type('Model{}ModelType'.format(name), (graphene.ObjectType,), {
                'attrs': graphene.Field(ModelAttrsType),
                'allAttrs': graphene.Field(RawScalar),
                'lookups': graphene.List(RawScalar)
            })
            ModelListType = type('Model{}ModelListType'.format(name), (graphene.ObjectType,), {
                'data': graphene.List(ModelType),
                'pagination': graphene.Field(PaginationResponseType)
            })

            def create_list_resolver(Model, mapper):
                def resolver(parent, info, filters=None, lookups=None, sort=None, pagination=None, search=None):
                    request = info.context.get('request')

                    if before_resolve is not None:
                        before_resolve(request=request, mapper=mapper)

                    return self.resolve_model_list(
                        MappedBase,
                        Model,
                        mapper,
                        info,
                        filters=filters,
                        lookups=lookups,
                        sort=sort,
                        pagination=pagination,
                        search=search
                    )
                return resolver

            query_attrs[name] = graphene.Field(
                ModelListType,
                filters=FiltersType,
                lookups=graphene.List(LookupsType),
                sort=SortType,
                pagination=PaginationType(),
                search=SearchType()
            )
            query_attrs['resolve_{}'.format(name)] = create_list_resolver(Model, mapper)

        return type('Query', (graphene.ObjectType,), query_attrs)

    def get_schema(self, request, draft, before_resolve=None):
        Query = self.get_query_type(request, draft, before_resolve)
        return graphene.Schema(query=Query, auto_camelcase=False)
