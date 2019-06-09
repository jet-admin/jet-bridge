from jet_bridge.exceptions.sql import SqlError
from jet_bridge.permissions import HasProjectPermissions
from jet_bridge.responses.base import Response
from jet_bridge.serializers.sql import SqlSerializer, SqlsSerializer
from jet_bridge.views.base.api import APIView


class SqlHandler(APIView):
    permission_classes = (HasProjectPermissions,)

    def post(self):
        serializer = SqlsSerializer(data=self.data) if 'queries' in self.data \
            else SqlSerializer(data=self.data)
        serializer.is_valid(raise_exception=True)

        try:
            response = Response(serializer.execute(serializer.validated_data))
            self.write_response(response)
        except SqlError as e:
            self.set_status(400)
            self.write_response(Response({'error': e.detail.string}))
