from jet_bridge.permissions import HasProjectPermissions
from jet_bridge.views.base.api import APIView


class MessageHandler(APIView):
    permission_classes = (HasProjectPermissions,)

    def post(self):
        pass
