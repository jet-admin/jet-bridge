from graphql import GraphQLError

from jet_bridge_base.db import connection_cache_set, connection_cache_get
from jet_bridge_base.exceptions.permission_denied import PermissionDenied
from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
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
        draft = request.get_argument('draft', False)
        schema_key = 'graphql_schema_draft' if draft else 'graphql_schema'

        schema = connection_cache_get(request, schema_key)
        if schema is None:
            def before_resolve(request, mapper, *args, **kwargs):
                request.context['model'] = mapper.selectable.name
                self.check_permissions(request)

            schema = GraphQLSchemaGenerator().get_schema(request, draft, before_resolve=before_resolve)
            connection_cache_set(request, schema_key, schema)

        if 'query' not in request.data:
            return JSONResponse({})

        query = request.data.get('query')
        result = schema.execute(query, variables={}, context_value={
            'request': request,
            'session': request.session
        })

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
