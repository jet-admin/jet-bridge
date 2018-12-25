from jet_bridge.permissions import HasProjectPermissions
from jet_bridge.responses.base import Response
from jet_bridge.serializers.sql import SqlSerializer
from jet_bridge.views.base.api import APIView


class SqlHandler(APIView):
    permission_classes = (HasProjectPermissions,)

    def post(self):
        serializer = SqlSerializer(data=self.data)
        serializer.is_valid(raise_exception=True)

        response = Response(serializer.execute())
        self.write_response(response)
