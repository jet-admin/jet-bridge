import time
from sqlalchemy import inspect

from jet_bridge_base.configuration import configuration
from jet_bridge_base.db import connections, pending_connections
from jet_bridge_base.permissions import AdministratorPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.sentry import sentry_controller
from jet_bridge_base.utils.classes import issubclass_safe
from jet_bridge_base.utils.common import format_size
from jet_bridge_base.utils.graphql import ModelFiltersType, ModelFiltersFieldType, ModelFiltersRelationshipType, \
    ModelLookupsType, ModelLookupsFieldType, ModelLookupsRelationshipType, ModelSortType, ModelAttrsType
from jet_bridge_base.utils.process import get_memory_usage
from jet_bridge_base.views.base.api import BaseAPIView


class StatusView(BaseAPIView):
    permission_classes = (AdministratorPermissions,)

    def map_connection_graphql_schema(self, schema):
        if not schema:
            return {'status': 'no_schema'}

        instance = schema.get('instance')
        tables_processed = schema.get('tables_processed', 0)
        tables_total = schema.get('tables_total')

        if instance:
            types_count = len(instance._type_map.values())
            filters_count = 0
            filters_fields_count = 0
            filters_relationships_count = 0
            lookups_count = 0
            lookups_fields_count = 0
            lookups_relationships_count = 0
            sort_count = 0
            attrs_count = 0
            get_schema_time = schema.get('get_schema_time')
            memory_usage_approx = schema.get('memory_usage_approx')

            for item in instance._type_map.values():
                if not hasattr(item, 'graphene_type'):
                    continue

                if issubclass_safe(item.graphene_type, ModelFiltersType):
                    filters_count += 1
                elif issubclass_safe(item.graphene_type, ModelFiltersFieldType):
                    filters_fields_count += 1
                elif issubclass_safe(item.graphene_type, ModelFiltersRelationshipType):
                    filters_relationships_count += 1
                elif issubclass_safe(item.graphene_type, ModelLookupsType):
                    lookups_count += 1
                elif issubclass_safe(item.graphene_type, ModelLookupsFieldType):
                    lookups_fields_count += 1
                elif issubclass_safe(item.graphene_type, ModelLookupsRelationshipType):
                    lookups_relationships_count += 1
                elif issubclass_safe(item.graphene_type, ModelSortType):
                    sort_count += 1
                elif issubclass_safe(item.graphene_type, ModelAttrsType):
                    attrs_count += 1

            return {
                'status': 'ok',
                'tables_processed': tables_processed,
                'tables_total': tables_total,
                'types': types_count,
                'filters': filters_count,
                'filters_fields': filters_fields_count,
                'filters_relationships': filters_relationships_count,
                'lookups': lookups_count,
                'lookups_fields': lookups_fields_count,
                'lookups_relationships': lookups_relationships_count,
                'sort': sort_count,
                'attrs': attrs_count,
                'get_schema_time': get_schema_time,
                'memory_usage_approx': memory_usage_approx,
                'memory_usage_approx_str': format_size(memory_usage_approx) if memory_usage_approx else None
            }
        else:
            return {
                'status': 'pending',
                'tables_processed': tables_processed,
                'tables_total': tables_total
            }

    def map_tunnel(self, tunnel):
        if not tunnel:
            return

        return {
            'is_active': tunnel.is_active,
            'local_address': '{}:{}'.format(tunnel.local_bind_host, tunnel.local_bind_port),
            'remote_address': '{}:{}'.format(tunnel.ssh_host, tunnel.ssh_port)
        }

    def map_connection(self, connection):
        cache = connection['cache']
        MappedBase = connection['MappedBase']
        column_count = 0
        relationships_count = 0

        for Model in MappedBase.classes:
            try:
                mapper = inspect(Model)
                column_count += len(mapper.columns)
                relationships_count += len(mapper.relationships)
            except Exception as e:
                sentry_controller.capture_exception(e)

        graphql_schema = self.map_connection_graphql_schema(cache.get('graphql_schema'))
        graphql_schema_draft = self.map_connection_graphql_schema(cache.get('graphql_schema_draft'))
        tunnel = self.map_tunnel(connection.get('tunnel'))
        last_request = connection.get('last_request')

        reflect_memory_usage_approx = connection.get('reflect_memory_usage_approx')

        return {
            'id': connection['id'],
            'name': connection['name'],
            'params_id': connection['params_id'],
            'project': connection.get('project'),
            'token': connection.get('token'),
            'tables': len(MappedBase.classes),
            'columns': column_count,
            'relationships': relationships_count,
            'graphql_schema': graphql_schema,
            'graphql_schema_draft': graphql_schema_draft,
            'init_start': connection.get('init_start'),
            'connect_time': connection.get('connect_time'),
            'reflect_time': connection.get('reflect_time'),
            'reflect_memory_usage_approx': reflect_memory_usage_approx,
            'reflect_memory_usage_approx_str': format_size(reflect_memory_usage_approx) if reflect_memory_usage_approx else None,
            'tunnel': tunnel,
            'last_request': last_request.isoformat() if last_request else None
        }

    def map_pending_connection(self, pending_connection):
        tunnel = self.map_tunnel(pending_connection.get('tunnel'))

        return {
            'id': pending_connection['id'],
            'name': pending_connection['name'],
            'project': pending_connection.get('project'),
            'token': pending_connection.get('token'),
            'init_start': pending_connection.get('init_start'),
            'tables_processed': pending_connection.get('tables_processed', 0),
            'tables_total': pending_connection.get('tables_total'),
            'tunnel': tunnel
        }

    def get(self, request, *args, **kwargs):
        now = time.time()
        uptime = round(now - configuration.init_time)
        memory_used = get_memory_usage()

        active_connections = []
        schema_generating_connections = []

        for connection in connections.values():
            cache = connection['cache']
            graphql_schema = cache.get('graphql_schema')
            graphql_schema_draft = cache.get('graphql_schema_draft')

            if graphql_schema and not graphql_schema.get('instance'):
                schema_generating_connections.append(connection)
            elif graphql_schema_draft and not graphql_schema_draft.get('instance'):
                schema_generating_connections.append(connection)
            else:
                active_connections.append(connection)

        return JSONResponse({
            'total_pending_connections': len(pending_connections.keys()),
            'total_schema_generating_connections': len(schema_generating_connections),
            'total_active_connections': len(active_connections),
            'pending_connections': map(lambda x: self.map_pending_connection(x), pending_connections.values()),
            'schema_generating_connections': map(lambda x: self.map_connection(x), schema_generating_connections),
            'active_connections': map(lambda x: self.map_connection(x), active_connections),
            'memory_used': memory_used,
            'memory_used_str': format_size(memory_used),
            'uptime': uptime
        })
