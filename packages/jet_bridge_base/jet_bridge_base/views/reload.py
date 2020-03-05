from jet_bridge_base.db import dispose_connection, get_request_connection
from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.views.base.api import APIView


class ReloadView(APIView):
    permission_classes = (HasProjectPermissions,)

    def required_project_permission(self):
        return {
            'permission_type': 'project',
            'permission_object': 'project_settings',
            'permission_actions': ''
        }

    def post(self, *args, **kwargs):
        result = dispose_connection(self.request)
        get_request_connection(self.request)
        return JSONResponse({
            'success': result
        })
