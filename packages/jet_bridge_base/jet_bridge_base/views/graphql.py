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

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        schema = connection_cache_get(request, 'graphql_schema')
        if schema is None:
            def before_resolve(request, mapper, *args, **kwargs):
                request.context['model'] = mapper.selectable.name
                self.check_permissions(request)

            schema = GraphQLSchemaGenerator().get_schema(request, before_resolve=before_resolve)
            connection_cache_set(request, 'graphql_schema', schema)

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
            return JSONResponse({'errors': map(lambda x: x.message, result.errors)})

        return JSONResponse({
            'data': result.data
        })
