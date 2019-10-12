from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.views.base.api import APIView


class MessageView(APIView):
    permission_classes = (HasProjectPermissions,)

    def post(self, *args, **kwargs):
        return JSONResponse()
