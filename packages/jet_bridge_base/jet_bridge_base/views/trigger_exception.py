from jet_bridge_base.permissions import AdministratorPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.views.base.api import BaseAPIView


class TriggerExceptionView(BaseAPIView):
    permission_classes = (AdministratorPermissions,)

    def get(self, request, *args, **kwargs):
        division_by_zero = 1 / 0
        return JSONResponse({
            'result': True
        })
