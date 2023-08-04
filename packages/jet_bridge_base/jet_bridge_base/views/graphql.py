import threading
import time
from datetime import timedelta

from graphql import GraphQLError

from jet_bridge_base.db import request_connection_cache, get_table_name, get_mapped_base, get_connection_id_short
from jet_bridge_base.exceptions.permission_denied import PermissionDenied
from jet_bridge_base.logger import logger
from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.utils.common import get_random_string
from jet_bridge_base.utils.graphql import GraphQLSchemaGenerator
from jet_bridge_base.utils.process import get_memory_usage_human, get_memory_usage
from jet_bridge_base.utils.track_database import track_database_async
from jet_bridge_base.views.base.api import APIView


class GraphQLView(APIView):
    permission_classes = (HasProjectPermissions,)

    def before_dispatch_permissions_check(self, request):
        pass

    def required_project_permission(self, request):
        return {
            'permission_type': 'model',
            'permission_object': request.context.get('model'),
            'permission_actions': 'r'
        }

    def map_gql_error(self, error):
        if isinstance(error, GraphQLError):
            return error.message
        else:
            return str(error)

    def wait_schema(self, request, schema_key, wait_schema):
        if not wait_schema:
            return

        id_short = get_connection_id_short(request)

        logger.info('[{}] Waiting GraphQL schema "{}"...'.format(id_short, wait_schema['id']))

        generated_condition = wait_schema['generated']
        with generated_condition:
            timeout = timedelta(minutes=10).total_seconds()
            generated_condition.wait(timeout=timeout)

        with request_connection_cache(request) as cache:
            cached_schema = cache.get(schema_key)
            if cached_schema and cached_schema['instance']:
                logger.info('[{}] Found GraphQL schema "{}"'.format(id_short, wait_schema['id']))
                return cached_schema['instance']
            else:
                logger.info('[{}] Not found GraphQL schema "{}"'.format(id_short, wait_schema['id']))

    def create_schema_object(self):
        new_schema_id = get_random_string(32)
        new_schema_generated = threading.Condition()

        return {
            'id': new_schema_id,
            'instance': None,
            'get_schema_time': None,
            'memory_usage_approx': None,
            'generated': new_schema_generated
        }

    def create_schema(self, request, schema_key, new_schema, draft):
        id_short = get_connection_id_short(request)
        memory_usage_before = get_memory_usage()

        try:
            logger.info('[{}] Generating GraphQL schema "{}"...'.format(id_short, new_schema['id']))

            def before_resolve(request, mapper, *args, **kwargs):
                MappedBase = get_mapped_base(request)
                request.context['model'] = get_table_name(MappedBase.metadata, mapper.selectable)
                self.check_permissions(request)

            def on_progress_updated(request, new_schema, current_name, i, total):
                if current_name is not None:
                    logger.info('[{}] Generating GraphQL schema "{}" ({} / {}) (Mem:{})...'.format(
                        id_short,
                        current_name,
                        i + 1,
                        total,
                        get_memory_usage_human()
                    ))

                with request_connection_cache(request) as cache:
                    cached_schema = cache.get(schema_key)

                    if cached_schema and cached_schema['id'] == new_schema['id']:
                        new_schema = {**cached_schema, 'tables_processed': i, 'tables_total': total}
                        cache[schema_key] = new_schema

            get_schema_start = time.time()
            schema = GraphQLSchemaGenerator().get_schema(
                request,
                draft,
                before_resolve=before_resolve,
                on_progress_updated=lambda name, i, total: on_progress_updated(request, new_schema, name, i, total)
            )
            get_schema_end = time.time()
            get_schema_time = round(get_schema_end - get_schema_start, 3)
            memory_usage_approx = get_memory_usage() - memory_usage_before

            with request_connection_cache(request) as cache:
                cached_schema = cache.get(schema_key)

                if cached_schema and cached_schema['id'] == new_schema['id']:
                    new_schema = {
                        **cached_schema,
                        'instance': schema,
                        'get_schema_time': get_schema_time,
                        'memory_usage_approx': memory_usage_approx
                    }
                    cache[schema_key] = new_schema

                    logger.info('[{}] Saved GraphQL schema "{}" (Mem:{})'.format(
                        id_short,
                        new_schema['id'],
                        get_memory_usage_human()
                    ))
                else:
                    logger.info('[{}] Ignoring GraphQL schema result "{}", existing: "{}"'.format(
                        id_short,
                        new_schema['id'],
                        cached_schema.get('id') if cached_schema else None
                    ))

            return schema
        except Exception as e:
            with request_connection_cache(request) as cache:
                cached_schema = cache.get(schema_key)

                if cached_schema and cached_schema['id'] == new_schema['id']:
                    del cache[schema_key]

            raise e
        finally:
            generated_condition = new_schema['generated']
            with generated_condition:
                generated_condition.notify_all()

    def get_schema(self, request, draft):
        schema_key = 'graphql_schema_draft' if draft else 'graphql_schema'
        wait_schema = None

        with request_connection_cache(request) as cache:
            cached_schema = cache.get(schema_key)

            if cached_schema and cached_schema['instance']:
                return cached_schema['instance']
            elif cached_schema and not cached_schema['instance']:
                wait_schema = cached_schema
            else:
                new_schema = self.create_schema_object()
                cache[schema_key] = new_schema

        if wait_schema:
            existing_schema = self.wait_schema(request, schema_key, wait_schema)
            if existing_schema:
                return existing_schema
            else:
                with request_connection_cache(request) as cache:
                    new_schema = self.create_schema_object()
                    cache[schema_key] = new_schema

        return self.create_schema(request, schema_key, new_schema, draft)

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        track_database_async(request)

        draft = bool(request.get_argument('draft', False))
        validate = bool(request.data.get('validate', True))

        if 'query' not in request.data:
            return JSONResponse({})

        try:
            schema = self.get_schema(request, draft)
        except Exception as e:
            return JSONResponse({'errors': ['Failed to get table schema: {}'.format(e)]})

        query = request.data.get('query')
        context_value = {
            'request': request,
            'session': request.session
        }
        result = schema.execute(
            query,
            variables={},
            context_value=context_value,
            validate=validate
        )

        if result.errors is not None and len(result.errors):
            error = result.errors[0]
            if hasattr(error, 'original_error'):
                error = error.original_error
            if isinstance(error, PermissionDenied):
                raise error
            return JSONResponse({'errors': map(lambda x: self.map_gql_error(x), result.errors)})

        return JSONResponse({
            'data': result.data
        })
