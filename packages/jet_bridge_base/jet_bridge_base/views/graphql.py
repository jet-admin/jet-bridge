import time

from graphql import GraphQLError

from jet_bridge_base.db import connection_cache_set, connection_cache_get, connection_cache
from jet_bridge_base.exceptions.permission_denied import PermissionDenied
from jet_bridge_base.logger import logger
from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.utils.common import get_random_string
from jet_bridge_base.utils.graphql import GraphQLSchemaGenerator
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

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        draft = bool(request.get_argument('draft', False))
        validate = bool(request.data.get('validate', True))

        schema_key = 'graphql_schema_draft' if draft else 'graphql_schema'
        schema = None
        new_schema = None

        with connection_cache(request) as cache:
            cached_schema = cache.get(schema_key)

            if cached_schema and cached_schema['instance']:
                schema = cached_schema['instance']
            else:
                new_schema_id = get_random_string(32)
                new_schema = {'id': new_schema_id, 'instance': None, 'get_schema_time': None}
                cache[schema_key] = new_schema

        if new_schema:
            logger.info('Generating GraphQL schema "{}"...'.format(new_schema['id']))

            def before_resolve(request, mapper, *args, **kwargs):
                request.context['model'] = mapper.selectable.name
                self.check_permissions(request)

            get_schema_start = time.time()
            schema = GraphQLSchemaGenerator().get_schema(request, draft, before_resolve=before_resolve)
            get_schema_end = time.time()
            get_schema_time = round(get_schema_end - get_schema_start, 3)

            with connection_cache(request) as cache:
                cached_schema = cache.get(schema_key)

                if cached_schema and cached_schema['id'] == new_schema['id']:
                    new_schema = {'id': new_schema['id'], 'instance': schema, 'get_schema_time': get_schema_time}
                    cache[schema_key] = new_schema

                    logger.info('Saved GraphQL schema "{}"'.format(new_schema['id']))
                else:
                    logger.info('Ignoring GraphQL schema result "{}", existing: ""'.format(
                        new_schema['id'],
                        cached_schema.get('id')
                    ))

        if 'query' not in request.data:
            return JSONResponse({})

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
