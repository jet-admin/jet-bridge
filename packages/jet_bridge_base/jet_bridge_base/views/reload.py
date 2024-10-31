from jet_bridge_base.db import dispose_request_connection, get_request_connection
from jet_bridge_base.db_types import remove_metadata_file
from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.utils.conf import get_conf
from jet_bridge_base.views.base.api import APIView


class ReloadView(APIView):
    permission_classes = (HasProjectPermissions,)

    def required_project_permission(self, request):
        return {
            'permission_type': 'project',
            'permission_object': 'project_settings',
            'permission_actions': ''
        }

    def post(self, request, *args, **kwargs):
        conf = get_conf(request)
        remove_metadata_file(conf)

        result = dispose_request_connection(request)
        get_request_connection(request)

        return JSONResponse({
            'success': result
        })
