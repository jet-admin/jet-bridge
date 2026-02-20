import re
import time
import graphene
from jet_bridge_base.utils.base62 import utf8_to_base62
from sqlalchemy.engine import Row
from sqlalchemy.orm import MANYTOONE, ONETOMANY, Query

from jet_bridge_base.db import get_mapped_base, get_engine, get_request_connection
from jet_bridge_base.db_types import desc_uniform, inspect_uniform, get_session_engine, queryset_count_optimized, \
    apply_default_ordering, queryset_search, queryset_group, aliased_uniform, MongoQueryset
from jet_bridge_base.db_types.sql import sql_load_database_table
from jet_bridge_base.filters import lookups
from jet_bridge_base.filters.filter import EMPTY_VALUES
from jet_bridge_base.filters.filter_for_dbfield import filter_for_column
from jet_bridge_base.models.model_relation_override import ModelRelationOverrideModel
from jet_bridge_base.serializers.model import get_model_serializer
from jet_bridge_base.store import store
from jet_bridge_base.utils.common import get_set_first, any_type_sorter, unique, flatten
from jet_bridge_base.utils.gql import RawScalar
from jet_bridge_base.utils.relations import parse_relationship_direction
from jet_bridge_base.utils.tables import get_table_name


class ModelFiltersType(graphene.InputObjectType):
    pass


class ModelFiltersFieldType(graphene.InputObjectType):
    pass


class ModelFiltersRelationshipType(graphene.InputObjectType):
    pass


class ModelLookupsType(graphene.InputObjectType):
    pass


class ModelLookupsFieldType(graphene.InputObjectType):
    pass


class ModelLookupsRelationshipType(graphene.InputObjectType):
    pass


class ModelSortType(graphene.InputObjectType):
    pass


class ModelAttrsType(graphene.ObjectType):
    pass


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


def get_model_filters_type_relationship_type(self, MappedBase, mapper, relationship, with_relations, depth):
    if not with_relations:
        return

    relationship_filters_type = self.get_model_relationship_filters_type(MappedBase, mapper, relationship, with_relations, depth)
    return relationship_filters_type()


def get_model_filters_type_not_type(self, MappedBase, mapper, with_relations, depth):
    if not with_relations:
        return

    return self.get_model_filters_type(MappedBase, mapper, depth + 1)


def get_model_field_filters_type_relation_type(self, MappedBase, relationship, with_relations, depth):
    if not with_relations:
        return

    relation_mapper = relationship['related_mapper']
    column_filters_type = self.get_model_filters_type(MappedBase, relation_mapper, depth + 1)
    return column_filters_type


def get_model_lookups_type_relation_type(self, MappedBase, mapper, relationship, with_relations, depth):
    if not with_relations:
        return

    relationship_lookups_type = self.get_model_relationship_lookups_type(MappedBase, mapper, relationship, with_relations, depth)
    return relationship_lookups_type()


def get_model_field_lookups_type_relation_type(self, MappedBase, mapper, column_name, with_relations, depth):
    if not with_relations:
        return

    for relationship in self.get_model_relationships(MappedBase, mapper):
        if relationship['direction'] != MANYTOONE or relationship['local_column_name'] != column_name:
            continue

        relation_mapper = relationship['related_mapper']
        lookups_type = self.get_model_lookups_type(MappedBase, relation_mapper, depth + 1)
        return lookups_type()


def get_model_relationship_lookups_type_relation_type(self, MappedBase, relationship, with_relations, depth):
    if not with_relations:
        return

    lookups_type = self.get_model_lookups_type(MappedBase, relationship['related_mapper'], depth + 1)
    return lookups_type()


def apply_dynamic_type(func, *arg, **kwargs):
    class DynamicInstance(graphene.Dynamic):
        def __init__(self, with_schema=False, _creation_counter=None):
            super(DynamicInstance, self).__init__(func, with_schema, _creation_counter)

        def get_type(self, schema=None):
            if schema and self.with_schema:
                return self.type(schema=schema, *arg, **kwargs)
            return self.type(*arg, **kwargs)

    return DynamicInstance()


class GraphQLSchemaGenerator(object):
    def __init__(self, base62=False):
        self.base62 = base62
        self.relationships_by_name = dict()
        self.relationships_by_clean_name = dict()
        self.model_filters_types = dict()
        self.model_filters_field_types = dict()
        self.model_filters_relationship_types = dict()
        self.model_lookups_types = dict()
        self.model_lookups_field_types = dict()
        self.model_lookups_relationship_types = dict()
        self.model_sort_types = dict()

    def clean_name(self, name):
        if self.base62:
            if name == '':
                return ''
            elif re.match(r'^[_a-zA-Z][_a-zA-Z0-9]*$', name) and name not in ['_meta', 'Meta']:
                return name
            else:
                name_base62 = utf8_to_base62(name)
                return '__BASE62__{}'.format(name_base62)
        else:
            if name == '_meta' or name == 'Meta':
                return '__meta'
            name = re.sub(r'[^_a-zA-Z0-9]', r'_', name)
            name = re.sub(r'^(\d)', r'_\1', name)
            return name

    def clean_keys(self, obj):
        pairs = map(lambda x: [self.clean_name(x[0]), x[1]], obj.items())
        return dict(pairs)

    def get_queryset(self, request, Model, only_columns=None):
        mapper = inspect_uniform(Model)
        pks = mapper.primary_key

        if only_columns:
            only_columns_name = list(map(lambda x: x.name, only_columns))
            missing_pks = list(filter(lambda x: x.name not in only_columns_name, pks))

            if len(missing_pks):
                only_columns = [*missing_pks, *only_columns]

            queryset = request.session.query(*only_columns)
        else:
            queryset = request.session.query(Model)

        mapper = inspect_uniform(Model)
        auto_pk = getattr(mapper.tables[0], '__jet_auto_pk__', False) if len(mapper.tables) else None
        if auto_pk:
            queryset = queryset.filter(mapper.primary_key[0].isnot(None))

        if not auto_pk and get_session_engine(request.session) in ['postgresql', 'mysql']:
            queryset = queryset.group_by(*pks)

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

            mapper = inspect_uniform(Model)
            name = get_table_name(MappedBase.metadata, mapper.selectable)

            model_relationships_overrides = relationships_overrides.get(name, [])

            for override in model_relationships_overrides:
                direction = parse_relationship_direction(override.direction)
                local_column = getattr(Model, override.local_field, None)

                if local_column is None:
                    continue

                related_name = override.related_model
                related_model = MappedBase.classes.get(related_name)

                if not related_model and '.' in related_name:
                    schema, table = related_name.split('.', 1)
                    engine = get_engine(request)
                    related_model = sql_load_database_table(engine, MappedBase, schema, table)

                if not related_model:
                    continue

                related_mapper = inspect_uniform(related_model)
                related_column = getattr(related_model, override.related_field, None)

                if related_column is None:
                    continue

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

            for relationship in mapper.relationships.values():
                local_column = get_set_first(relationship.local_columns)
                relation_column = get_set_first(relationship.remote_side)

                if relationship.direction == MANYTOONE:
                    table = relationship.mapper.tables[0]
                    related_name = get_table_name(MappedBase.metadata, table)
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
                    table = relationship.mapper.tables[0]
                    related_name = get_table_name(MappedBase.metadata, table)
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

            result[name] = model_relationships

        return result

    def clean_relationships_by_name(self, relationships):
        def map_model_relations(x):
            return self.clean_name(x[0]), x[1]

        def map_models(x):
            return x[0], dict(map(lambda r: map_model_relations(r), x[1].items()))

        return dict(map(lambda x: map_models(x), relationships.items()))

    def get_model_columns_by_clean_name(self, MappedBase, mapper):
        table = mapper.tables[0]
        name = get_table_name(MappedBase.metadata, table)
        Model = MappedBase.classes.get(name)
        return dict(map(lambda x: (self.clean_name(x), getattr(Model, x)), mapper.columns.keys()))

    def get_model_relationships(self, MappedBase, mapper):
        name = get_table_name(MappedBase.metadata, mapper.selectable)
        return self.relationships_by_name.get(name, {}).values()

    def get_model_relationships_by_name(self, MappedBase, mapper):
        name = get_table_name(MappedBase.metadata, mapper.selectable)
        return self.relationships_by_name.get(name, {})

    def get_model_relationships_by_clean_name(self, MappedBase, mapper):
        name = get_table_name(MappedBase.metadata, mapper.selectable)
        return self.relationships_by_clean_name.get(name, {})

    def filter_queryset(self, request, MappedBase, queryset, mapper, filters, parent_relations=None, exclude=False):
        parent_relations = parent_relations or []

        for filters_item in filters:
            filters_item_dict = dict(filters_item)

            for filter_name, filter_lookups in filters_item_dict.items():
                if filter_name == '_not_':
                    queryset = self.filter_queryset(
                        request,
                        MappedBase,
                        queryset,
                        mapper,
                        filter_lookups,
                        parent_relations,
                        exclude=True
                    )
                    continue

                columns_by_clean_name = self.get_model_columns_by_clean_name(MappedBase, mapper)
                column = columns_by_clean_name.get(filter_name)
                filter_relationship = self.get_model_relationships_by_clean_name(MappedBase, mapper).get(filter_name)

                if filter_relationship is not None:
                    filter_lookups_dict = dict(filter_lookups)

                    for lookup_name, lookup_value in filter_lookups_dict.items():
                        if lookup_name == 'relation':
                            relation_mapper = filter_relationship['related_mapper']
                            queryset = self.filter_queryset(
                                request,
                                MappedBase,
                                queryset,
                                relation_mapper,
                                lookup_value,
                                [*parent_relations, filter_relationship],
                                exclude
                            )
                elif column is not None:
                    filter_lookups_dict = dict(filter_lookups)

                    for lookup_name, lookup_value in filter_lookups_dict.items():
                        if lookup_name == 'relation':
                            for relationship in self.get_model_relationships(MappedBase, mapper):
                                if relationship['direction'] != MANYTOONE or relationship['local_column_name'] != column.name:
                                    continue

                                relation_mapper = relationship['related_mapper']
                                queryset = self.filter_queryset(
                                    request,
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
                                    related_model = aliased_uniform(relationship['related_model'])
                                    related_column = getattr(related_model, relationship['related_column'].name)
                                    local_column = getattr(last_related_model, relationship['local_column'].name) if last_related_model else relationship['local_column']
                                    queryset = queryset.join(
                                        related_model,
                                        related_column == local_column
                                    )
                                    last_related_model = related_model

                                column = getattr(last_related_model, column.name)

                            item = filter_for_column(column)
                            lookup = lookups.by_gql.get(lookup_name)
                            filters_instance = item['filter_class'](
                                name=column.key,
                                column=column,
                                lookup=lookup,
                                exclude=False
                            )

                            lookup_value = filters_instance.clean_value(lookup_value)
                            if lookup_value not in EMPTY_VALUES:
                                criterion = filters_instance.get_lookup_criterion(queryset, lookup_value)
                                criterion = ~criterion if exclude else criterion

                                queryset = queryset.filter(criterion)

        return queryset

    def search_queryset(self, queryset, mapper, search):
        if search is not None:
            query = search['query']
            queryset = queryset_search(queryset, mapper, query)

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

        lookup_item_dict = dict(lookup_item)

        for lookup_name, lookup_data in lookup_item_dict.items():
            columns_by_clean_name = self.get_model_columns_by_clean_name(MappedBase, mapper)
            column = columns_by_clean_name.get(lookup_name)
            relationship = self.get_model_relationships_by_clean_name(MappedBase, mapper).get(lookup_name)

            if relationship is not None:
                lookup_result = {}
                local_column = relationship['local_column']
                lookup_values = sorted(unique(flatten(map(lambda x: getattr(x, local_column.name), models))), key=any_type_sorter)

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

                    aggregate_column = getattr(relation_model, aggregate_column_name, None)
                    if aggregate_column is not None:
                        queryset = request.session.query(relation_model).filter(relation_column.in_(lookup_values))
                        groups = queryset_group(relation_model, queryset, {
                            'y_func': lookup_data['aggregate']['func'],
                            'y_column': aggregate_column.name,
                            'x_columns': [relation_column.name],
                            'x_lookups': ['plain']
                        })

                        if isinstance(groups, (Query, MongoQueryset)):
                            groups = groups.limit(1000)
                        else:
                            groups = groups[:1000]

                        groups_dict = dict(map(lambda x: (x['group'], x['y_func']), groups))

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
                lookup_values = sorted(unique(flatten(map(lambda x: getattr(x, column.name), models))), key=any_type_sorter)

                lookup_result['return'] = lookup_data.get('return', False)
                lookup_result['return_list'] = lookup_data.get('returnList', False)
                lookup_result['Model'] = Model
                lookup_result['mapper'] = mapper
                lookup_result['model_values'] = list(map(lambda x: {'instance': x, 'value': getattr(x, column.name)}, models))
                lookup_result['source_column'] = column.name

                if 'relation' in lookup_data:
                    for relationship in self.get_model_relationships(MappedBase, mapper):
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

            values = list(flatten(map(lambda x: x['value'], model_values)))

            if lookup_data['return']:
                if lookup_data['return_list']:
                    item_result['value'] = values
                else:
                    item_result['value'] = values[0] if len(values) else None

            if 'related' in lookup_data:
                item_result['related'] = self.filter_lookup_models(
                    lookup_data['related'],
                    lambda x: getattr(x, lookup_data['related_column'], None) in values
                )

            if 'aggregated_values' in lookup_data:
                model_values = list(filter(
                    lambda x: getattr(x['instance'], lookup_data['source_column'], None) in values,
                    lookup_data['aggregated_values']
                ))
                item_result['aggregated'] = model_values[0]['value'] if len(model_values) else 0

            result[lookup_name] = item_result

        return result

    def map_sort_order_field(self, MappedBase, mapper, name, options):
        descending = options.get('descending', False)

        columns_by_clean_name = self.get_model_columns_by_clean_name(MappedBase, mapper)
        column = columns_by_clean_name.get(name)

        if column is None:
            return

        if descending:
            column = desc_uniform(column)

        return column

    def sort_queryset(self, queryset, MappedBase, mapper, sort):
        total_order_by = []

        for item in sort:
            item_dict = dict(item)

            order_by = map(lambda x: self.map_sort_order_field(MappedBase, mapper, x[0], x[1]), item_dict.items())
            order_by = filter(lambda x: x is not None, order_by)
            total_order_by.extend(order_by)

        queryset = queryset.order_by(*total_order_by)

        table = mapper.tables[0]
        name = get_table_name(MappedBase.metadata, table)
        Model = MappedBase.classes.get(name)
        queryset = apply_default_ordering(Model, queryset)

        return queryset

    def get_pagination_limit(self, pagination):
        default_limit = 20
        limit = pagination.get('limit', default_limit)

        if limit > 1000:
            limit = 1000
        elif limit < 0:
            limit = default_limit

        return limit

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
        table_name = get_table_name(MappedBase.metadata, mapper.selectable)
        model_name = self.clean_name(table_name)
        cls_name = 'Model{}FiltersType'.format(model_name)

        if cls_name in self.model_filters_types:
            return graphene.List(self.model_filters_types[cls_name])

        attrs = {}

        for column in mapper.columns:
            column_filters_type = self.get_model_field_filters_type(MappedBase, mapper, column, with_relations, depth)
            attr_name = self.clean_name(column.name)
            attrs[attr_name] = column_filters_type()

        for relationship in self.get_model_relationships(MappedBase, mapper):
            if relationship['direction'] != ONETOMANY:
                continue

            attr_name = self.clean_name(relationship['name'])
            attrs[attr_name] = apply_dynamic_type(get_model_filters_type_relationship_type, self, MappedBase, mapper, relationship, with_relations, depth)

        attrs['_not_'] = apply_dynamic_type(get_model_filters_type_not_type, self, MappedBase, mapper, with_relations, depth)

        cls = type(cls_name, (ModelFiltersType,), attrs)
        self.model_filters_types[cls_name] = cls
        return graphene.List(cls)

    def get_model_field_filters_type_relationship(self, MappedBase, mapper, column_name):
        for relationship in self.get_model_relationships(MappedBase, mapper):
            if relationship['direction'] != MANYTOONE or relationship['local_column_name'] != column_name:
                continue

            return relationship

    def get_model_field_filters_type(self, MappedBase, mapper, column, with_relations, depth=1):
        table_name = get_table_name(MappedBase.metadata, mapper.selectable)
        model_name = self.clean_name(table_name)
        column_name = self.clean_name(column.name)
        dbfield_filter = filter_for_column(column)
        relationship = self.get_model_field_filters_type_relationship(MappedBase, mapper, column_name) if with_relations else None
        cls_name = 'Model{}Column{}FiltersType'.format(model_name, column_name) if relationship \
            else 'Lookups{}FiltersType'.format(dbfield_filter['lookups_name'])

        if cls_name in self.model_filters_field_types:
            return self.model_filters_field_types[cls_name]

        attrs = {}

        for lookup in dbfield_filter['lookups']:
            gql_lookup = lookups.gql.get(lookup)
            gql_scalar = lookups.gql_scalar.get(lookup, RawScalar())
            attrs[gql_lookup] = gql_scalar

        if relationship:
            attrs['relation'] = apply_dynamic_type(get_model_field_filters_type_relation_type, self, MappedBase, relationship, with_relations, depth)

        cls = type(cls_name, (ModelFiltersFieldType,), attrs)
        self.model_filters_field_types[cls_name] = cls
        return cls

    def get_model_relationship_filters_type(self, MappedBase, mapper, relationship, with_relations, depth=1):
        table_name = get_table_name(MappedBase.metadata, mapper.selectable)
        model_name = self.clean_name(table_name)
        relationship_key = self.clean_name(relationship['name'])
        cls_name = 'Model{}Relation{}RelationshipType'.format(model_name, relationship_key)

        if cls_name in self.model_filters_relationship_types:
            return self.model_filters_relationship_types[cls_name]

        attrs = {}

        lookups_type = self.get_model_filters_type(MappedBase, relationship['related_mapper'], depth + 1)
        attrs['relation'] = lookups_type

        cls = type(cls_name, (ModelFiltersRelationshipType,), attrs)
        self.model_filters_relationship_types[cls_name] = cls
        return cls

    def get_model_lookups_type(self, MappedBase, mapper, depth=1):
        with_relations = depth <= 4
        table_name = get_table_name(MappedBase.metadata, mapper.selectable)
        model_name = self.clean_name(table_name)
        cls_name = 'Model{}LookupsType'.format(model_name)

        if cls_name in self.model_lookups_types:
            return self.model_lookups_types[cls_name]

        attrs = {}

        for column in mapper.columns:
            column_lookups_type = self.get_model_field_lookups_type(MappedBase, mapper, column, with_relations, depth)
            attr_name = self.clean_name(column.name)
            attrs[attr_name] = column_lookups_type()

        for relationship in self.get_model_relationships(MappedBase, mapper):
            if relationship['direction'] != ONETOMANY:
                continue

            attr_name = self.clean_name(relationship['name'])
            attrs[attr_name] = apply_dynamic_type(get_model_lookups_type_relation_type, self, MappedBase, mapper, relationship, with_relations, depth)

        cls = type(cls_name, (ModelLookupsType,), attrs)
        self.model_lookups_types[cls_name] = cls
        return cls

    def get_model_field_lookups_type_relationship(self, MappedBase, mapper, column_name):
        for relationship in self.get_model_relationships(MappedBase, mapper):
            if relationship['direction'] != MANYTOONE or relationship['local_column_name'] != column_name:
                continue

            return relationship

    def get_model_field_lookups_type(self, MappedBase, mapper, column, with_relations, depth=1):
        table_name = get_table_name(MappedBase.metadata, mapper.selectable)
        model_name = self.clean_name(table_name)
        column_name = self.clean_name(column.name)
        relationship = self.get_model_field_lookups_type_relationship(MappedBase, mapper, column_name) if with_relations else None
        cls_name = 'Model{}Column{}LookupsFieldType'.format(model_name, column_name) if relationship \
            else 'LookupsFieldType'

        if cls_name in self.model_lookups_field_types:
            return self.model_lookups_field_types[cls_name]

        attrs = {
            'return': graphene.Boolean(),
            'returnList': graphene.Boolean()
        }

        if relationship:
            attrs['relation'] = apply_dynamic_type(get_model_field_lookups_type_relation_type, self, MappedBase, mapper, column_name, with_relations, depth)

        cls = type(cls_name, (ModelLookupsFieldType,), attrs)
        self.model_lookups_field_types[cls_name] = cls
        return cls

    def get_model_relationship_lookups_type(self, MappedBase, mapper, relationship, with_relations, depth=1):
        table_name = get_table_name(MappedBase.metadata, mapper.selectable)
        model_name = self.clean_name(table_name)
        relationship_key = self.clean_name(relationship['name'])
        cls_name = 'Model{}Relation{}LookupsRelationshipType'.format(model_name, relationship_key)

        if cls_name in self.model_lookups_relationship_types:
            return self.model_lookups_relationship_types[cls_name]

        attrs = {
            'aggregate': AggregateType()
        }

        attrs['relation'] = get_model_relationship_lookups_type_relation_type(self, MappedBase, relationship, with_relations, depth)

        cls = type(cls_name, (ModelLookupsRelationshipType,), attrs)
        self.model_lookups_relationship_types[cls_name] = cls
        return cls

    def get_model_sort_type(self, MappedBase, mapper):
        table_name = get_table_name(MappedBase.metadata, mapper.selectable)
        model_name = self.clean_name(table_name)
        cls_name = 'Model{}SortType'.format(model_name)

        if cls_name in self.model_sort_types:
            return graphene.List(self.model_sort_types[cls_name])

        attrs = {}

        for column in mapper.columns:
            attr_name = self.clean_name(column.name)
            attrs[attr_name] = FieldSortType()

        cls = type(cls_name, (ModelSortType,), attrs)
        self.model_sort_types[cls_name] = cls
        return graphene.List(cls)

    def get_model_attrs_type(self, MappedBase, mapper):
        table_name = get_table_name(MappedBase.metadata, mapper.selectable)
        name = self.clean_name(table_name)
        attrs = {}

        for column in mapper.columns:
            attr_name = self.clean_name(column.name)
            attrs[attr_name] = RawScalar()

        return type('Model{}RecordAttrsType'.format(name), (ModelAttrsType,), attrs)

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

    def resolve_model_list(self, MappedBase, Model, mapper, info, filters=None, lookups=None, sort=None, pagination=None, search=None):
        try:
            filters = filters or []
            lookups = lookups or []
            sort = sort or []
            pagination = pagination or {}

            request = info.context.get('request')
            request.apply_rls_if_enabled()

            field_selections = self.get_selections(info, ['data', 'attrs']) or []
            field_names = list(map(lambda x: x.name.value, field_selections))
            data_selections = self.get_selections(info, ['data']) or []
            data_names = list(map(lambda x: x.name.value, data_selections))
            model_attrs = dict(map(lambda x: [self.clean_name(x), getattr(Model, x)], dir(Model)))
            only_columns = list(filter(lambda x: x is not None, map(lambda x: model_attrs.get(x), field_names))) \
                if len(field_names) and 'allAttrs' not in data_names else None

            queryset = self.get_queryset(request, Model, only_columns)

            queryset = self.filter_queryset(request, MappedBase, queryset, mapper, filters)
            queryset = self.search_queryset(queryset, mapper, search)
            queryset = self.sort_queryset(queryset, MappedBase, mapper, sort)

            data_query_start = time.time()
            queryset_page = list(self.paginate_queryset(queryset, pagination))
            data_query_end = time.time()

            request.context['graphql_data_query_time'] = round(data_query_end - data_query_start, 3)

            serializer_class = get_model_serializer(Model)
            serializer_context = {**info.context}

            queryset_page_lookups = self.get_models_lookups(request, MappedBase, queryset_page, Model, mapper, lookups)

            def map_queryset_page_item(row):
                if isinstance(row, Row):
                    data = dict(row)
                else:
                    data = dict(map(lambda x: (self.clean_name(x.name), getattr(row, x.name)), mapper.columns))

                serializer = serializer_class(instance=data, context=serializer_context)
                serialized = serializer.representation_data
                serialized = self.clean_keys(serialized)

                return {
                    'attrs': serialized,
                    'allAttrs': serialized,
                    'lookups': list(map(
                        lambda x: self.filter_lookup_models(x, lambda instance: instance == row),
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
                    count_query_start = time.time()
                    if offset == 0 and len(queryset_page) < limit:
                        count = len(queryset_page)
                    elif page == 1 and len(queryset_page) < limit:
                        count = len(queryset_page)
                    else:
                        count = queryset_count_optimized(request.session, queryset)
                    result['pagination']['count'] = count
                    count_query_end = time.time()

                    if offset is not None:
                        result['pagination']['hasMore'] = offset + limit < count
                    elif page is not None:
                        result['pagination']['hasMore'] = page * limit < count

                    if result['pagination']['hasMore'] is False and len(result['data']) == limit:
                        # count may be inaccurate
                        result['pagination']['hasMore'] = True

                    request.context['graphql_count_query_time'] = round(count_query_end - count_query_start, 3)

            return result
        except Exception as e:
            raise e

    def get_query_type(self, request, draft, before_resolve=None, on_progress_updated=None):
        MappedBase = get_mapped_base(request)

        if len(MappedBase.classes) == 0:
            raise Exception('No tables found')

        query_attrs = {}

        self.relationships_by_name = self.get_relationships(request, MappedBase, draft)
        self.relationships_by_clean_name = self.clean_relationships_by_name(self.relationships_by_name)

        i = 0
        total = len(MappedBase.classes)

        for Model in MappedBase.classes:
            # Wait to allow other threads execution
            time.sleep(0.01)

            mapper = inspect_uniform(Model)
            table = mapper.tables[0]
            name = get_table_name(MappedBase.metadata, table)
            name = self.clean_name(name)

            if on_progress_updated:
                on_progress_updated(name, i, total)

            FiltersType = self.get_model_filters_type(MappedBase, mapper)
            LookupsType = self.get_model_lookups_type(MappedBase, mapper)
            SortType = self.get_model_sort_type(MappedBase, mapper)
            ModelAttrsType = self.get_model_attrs_type(MappedBase, mapper)
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

            i += 1

        if on_progress_updated:
            on_progress_updated(None, total, total)

        return type('Query', (graphene.ObjectType,), query_attrs)

    def get_schema(self, request, draft, before_resolve=None, on_progress_updated=None):
        Query = self.get_query_type(request, draft, before_resolve, on_progress_updated)
        return graphene.Schema(query=Query, auto_camelcase=False)
