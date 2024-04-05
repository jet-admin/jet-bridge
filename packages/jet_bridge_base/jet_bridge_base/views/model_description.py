import json
import re

from jet_bridge_base import status
from jet_bridge_base.models.model_relation_override import ModelRelationOverrideModel
from jet_bridge_base.responses.base import Response
from jet_bridge_base.store import store
from jet_bridge_base.utils.crypt import get_sha256_hash
from jet_bridge_base.utils.relations import relationship_direction_to_str
from sqlalchemy import inspect, String, Enum, Date
from sqlalchemy.orm import MANYTOONE, ONETOMANY
from sqlalchemy.sql.elements import TextClause

from jet_bridge_base.db import get_mapped_base, get_request_connection, get_table_name, request_connection_cache, \
    MODEL_DESCRIPTIONS_RESPONSE_CACHE_KEY, MODEL_DESCRIPTIONS_HASH_CACHE_KEY
from jet_bridge_base.models import data_types
from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.serializers.model_description import ModelDescriptionSerializer
from jet_bridge_base.utils.common import merge, get_set_first
from jet_bridge_base.utils.db_types import sql_to_map_type, sql_to_db_type
from jet_bridge_base.views.base.api import APIView


def is_column_has_default(column):
    return column.autoincrement or column.default or column.server_default


def is_column_optional(column):
    return is_column_has_default(column) or column.nullable


def is_column_required(column, primary_key_auto):
    if primary_key_auto:
        return True
    else:
        return not is_column_optional(column)


def map_column_default(column):
    if column.server_default is not None:
        if hasattr(column.server_default, 'arg') and isinstance(column.server_default.arg, TextClause):
            value = column.server_default.arg.text
            if value.lower() == 'now()':
                return {
                    'default_type': 'datetime_now'
                }
            elif value.lower() == 'uuid_generate_v4()':
                return {
                    'default_type': 'uuid'
                }
            elif value.lower() == 'true':
                return {
                    'default_type': 'value',
                    'default_value': True
                }
            elif value.lower() == 'false':
                return {
                    'default_type': 'value',
                    'default_value': False
                }

            value_regex = re.search("^'(?P<value>.+)'::(?P<type>.+)$", value)
            if value_regex:
                match = value_regex.groupdict()
                return {
                    'default_type': 'value',
                    'default_value': match['value']
                }

            nextval_regex = re.search("^nextval\((?P<value>.+)\)$", value)
            if nextval_regex:
                match = nextval_regex.groupdict()
                return {
                    'default_type': 'sequence',
                    'default_value': match['value']
                }


def map_column(metadata, column, editable, primary_key_auto):
    params = {}
    data_source_field = None
    data_source_name = None
    data_source_params = None
    data_source_order_after = None
    data_source_hidden = None

    try:
        map_type = sql_to_map_type(column.type)
    except:
        map_type = 'NullType'

    try:
        db_type = sql_to_db_type(column.type)
    except:
        db_type = 'NullType'

    if column.foreign_keys:
        foreign_key = next(iter(column.foreign_keys))
        map_type = data_types.FOREIGN_KEY
        params['related_model'] = {
            'model': get_table_name(metadata, foreign_key.column.table)
        }

        table_primary_keys = foreign_key.column.table.primary_key.columns.keys()
        table_primary_key = table_primary_keys[0] if len(table_primary_keys) > 0 else None

        if not table_primary_key or foreign_key.column.name != table_primary_key:
            params['custom_primary_key'] = foreign_key.column.name

    if isinstance(column.type, Date):
        params['date'] = True
        params['time'] = False

    if isinstance(column.type, Enum):
        params['options'] = map(lambda x: {'name': x, 'value': x}, column.type.enums)

    if isinstance(column.type, String):
        params['length'] = column.type.length

    try:
        from geoalchemy2 import types
        if isinstance(column.type, types.Geography):
            params['output_format'] = 'postgresql'
    except ImportError:
        pass

    required = is_column_required(column, primary_key_auto)

    if column.comment:
        try:
            data_source_meta = json.loads(column.comment)

            if not isinstance(data_source_meta, dict):
                raise ValueError

            meta_field = data_source_meta.get('field')
            meta_name = data_source_meta.get('name')
            meta_params = data_source_meta.get('params')
            meta_order_after = data_source_meta.get('order_after')
            meta_hidden = data_source_meta.get('hidden')

            if meta_field is not None:
                data_source_field = meta_field
            if meta_name is not None:
                data_source_name = meta_name
            if meta_params is not None and isinstance(meta_params, dict):
                data_source_params = meta_params
            if meta_order_after is not None:
                data_source_order_after = meta_order_after
            if meta_hidden is not None:
                data_source_hidden = meta_hidden
        except ValueError:
            pass

    result = {
        'name': column.name,
        'db_column': column.name,
        'field': map_type,
        'db_field': db_type,
        'filterable': True,
        'required': required,
        'null': column.nullable,
        'editable': editable,
        'params': params,
        'data_source_field': data_source_field,
        'data_source_name': data_source_name,
        'data_source_params': data_source_params,
        'data_source_order_after': data_source_order_after,
        'data_source_hidden': data_source_hidden
    }

    server_default = map_column_default(column)
    if server_default:
        result['default_type'] = server_default['default_type']
        if 'default_value' in server_default:
            result['default_value'] = server_default['default_value']

    return result


def is_column_primary_key_auto(primary_key, primary_key_auto, column):
    return primary_key is not None and column.name == primary_key.name and primary_key_auto


def map_table_column(metadata, table, column, editable):
    primary_key = table.primary_key.columns[0]
    primary_key_auto = getattr(table, '__jet_auto_pk__', False) if table is not None else None

    return map_column(
        metadata,
        column,
        editable,
        is_column_primary_key_auto(primary_key, primary_key_auto, column)
    )


def map_relationship(metadata, relationship):
    local_field = get_set_first(relationship.local_columns)
    related_field = get_set_first(relationship.remote_side)
    direction = relationship_direction_to_str(relationship.direction)

    result = {
        'name': relationship.key,
        'direction': direction,
        'local_field': local_field.name,
        'related_model': get_table_name(metadata, relationship.target),
        'related_field': related_field.name
    }

    return result


def map_relationship_override(override):
    result = {
        'name': override.name,
        'direction': override.direction,
        'local_field': override.local_field,
        'related_model': override.related_model,
        'related_field': override.related_field
    }

    return result


# def map_relation(relation):
#     field = None
#
#     if relation.direction == ONETOMANY:
#         field = 'ManyToOneRel'
#
#     return {
#         'name': relation.key,
#         'related_model': {
#             'model': relation.table.name
#         },
#         'field': field,
#         'related_model_field': relation.primaryjoin.right.name,
#         'through': None
#     }
#
# def table_relations(mapper):
#     return list(map(map_relation, filter(lambda x: x.direction == ONETOMANY and hasattr(x, 'table'), mapper.relationships)))
#
# def table_m2m_relations(mapper):
#     result = []
#     name = mapper.selectable.fullname
#
#     for relation in mapper.relationships:
#         if relation.direction != ONETOMANY or not hasattr(relation, 'table'):
#             continue
#
#         m2m_relationships = relation.mapper.relationships.values()
#
#         if len(m2m_relationships) != 2:
#             continue
#
#         if len(relation.table.columns) > 5:
#             continue
#
#         self_relationship = m2m_relationships[1] if m2m_relationships[1].table.fullname == name else \
#         m2m_relationships[0]
#         other_relationship = m2m_relationships[0] if self_relationship == m2m_relationships[1] else \
#         m2m_relationships[1]
#
#         result.append({
#             'name': 'M2M {} {}'.format(self_relationship.table.fullname, other_relationship.table.fullname),
#             'related_model': {
#                 'model': other_relationship.table.fullname
#             },
#             'field': 'ManyToManyField',
#             'related_model_field': self_relationship.table.fullname,
#             'through': {'model': relation.table.fullname}
#         })
#
#     return result

def map_table(MappedBase, cls, relationships_overrides, hidden):
    mapper = inspect(cls)
    table = mapper.tables[0]
    name = get_table_name(MappedBase.metadata, table)
    primary_key = mapper.primary_key[0]
    primary_key_auto = getattr(table, '__jet_auto_pk__', False) if table is not None else None
    is_view = getattr(table, '__jet_is_view__', False) if table is not None else False
    non_editable = []
    model_relationships_overrides = relationships_overrides.get(name)

    from jet_bridge_base.configuration import configuration
    additional = configuration.get_model_description(name)

    data_source_name = None
    data_source_name_plural = None
    data_source_order_after = None
    data_source_hidden = None

    if table.comment:
        try:
            data_source_meta = json.loads(table.comment)

            if not isinstance(data_source_meta, dict):
                raise ValueError

            meta_name = data_source_meta.get('name')
            meta_name_plural = data_source_meta.get('name_plural')
            meta_order_after = data_source_meta.get('order_after')
            meta_hidden = data_source_meta.get('hidden')

            if meta_name is not None:
                data_source_name = meta_name
            if meta_name_plural is not None:
                data_source_name_plural = meta_name_plural
            if meta_order_after is not None:
                data_source_order_after = meta_order_after
            if meta_hidden is not None:
                data_source_hidden = meta_hidden
        except ValueError:
            pass

    result = {
        'model': name,
        'db_table': name,
        'fields': list(map(lambda x: map_column(
            MappedBase.metadata,
            x,
            x.name not in non_editable,
            is_column_primary_key_auto(primary_key, primary_key_auto, x)
        ), mapper.columns)),
        'relations': sorted(
            list(map(lambda x: map_relationship(MappedBase.metadata, x), filter(lambda x: x.direction in [MANYTOONE, ONETOMANY], mapper.relationships))),
            key=lambda x: x['name']
        ),
        'relation_overrides': sorted(
            list(map(lambda x: map_relationship_override(x), model_relationships_overrides)),
            key=lambda x: x['name']
        ) if model_relationships_overrides else None,
        'hidden': name in hidden or name in configuration.get_hidden_model_description(),
        # 'relations': table_relations(mapper) + table_m2m_relations(mapper),
        'primary_key_field': primary_key.name if primary_key is not None else None,
        'primary_key_auto': primary_key_auto,
        'is_view': is_view,
        'data_source_name': data_source_name,
        'data_source_name_plural': data_source_name_plural,
        'data_source_order_after': data_source_order_after,
        'data_source_hidden': data_source_hidden
    }

    if additional:
        result = merge(result, additional)

    return result


class ModelDescriptionView(APIView):
    serializer_class = ModelDescriptionSerializer
    permission_classes = (HasProjectPermissions,)

    def get_queryset(self, request):
        hidden = ['__jet__token']
        MappedBase = get_mapped_base(request)
        relationships_overrides = {}
        draft = bool(request.get_argument('draft', False))

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

        return sorted(
            list(map(lambda x: map_table(MappedBase, x, relationships_overrides, hidden), MappedBase.classes)),
            key=lambda x: x['model']
        )

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset(request)
        serializer = self.serializer_class(instance=queryset, many=True)
        cid = request.get_argument('cid', None)
        client_cache_enabled = cid is not None

        with request_connection_cache(request) as cache:
            rendered_data = cache.get(MODEL_DESCRIPTIONS_RESPONSE_CACHE_KEY)

            if rendered_data is not None:
                if client_cache_enabled:
                    rendered_data_hash = cache.get(MODEL_DESCRIPTIONS_HASH_CACHE_KEY, get_sha256_hash(rendered_data))
                else:
                    rendered_data_hash = None

                if client_cache_enabled:
                    not_modified_response = self.get_not_modified_response(request, rendered_data_hash)
                    if not_modified_response:
                        return not_modified_response

                response = JSONResponse(rendered_data=rendered_data)

                if client_cache_enabled:
                    self.set_response_cache_headers(response, rendered_data_hash)

                return response
            else:
                response = JSONResponse(serializer.representation_data)
                rendered_data = response.render()

                cache[MODEL_DESCRIPTIONS_RESPONSE_CACHE_KEY] = rendered_data

                if client_cache_enabled:
                    rendered_data_hash = get_sha256_hash(rendered_data)
                    cache[MODEL_DESCRIPTIONS_HASH_CACHE_KEY] = rendered_data_hash

                    not_modified_response = self.get_not_modified_response(request, rendered_data_hash)
                    if not_modified_response:
                        return not_modified_response

                    self.set_response_cache_headers(response, rendered_data_hash)

                return response

    def set_response_cache_headers(self, response, rendered_data_hash):
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['ETag'] = '"%s"' % rendered_data_hash

    def get_not_modified_response(self, request, rendered_data_hash):
        if_none_match = request.headers.get('IF_NONE_MATCH')

        if if_none_match is not None and '"%s"' % rendered_data_hash == if_none_match:
            return Response(status=status.HTTP_304_NOT_MODIFIED)
