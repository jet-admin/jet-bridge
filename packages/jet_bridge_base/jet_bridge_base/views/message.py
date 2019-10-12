from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.optional_json import OptionalJSONResponse
from jet_bridge_base.serializers.message import MessageSerializer
from jet_bridge_base.views.base.api import APIView


class MessageView(APIView):
    permission_classes = (HasProjectPermissions,)

    def post(self, *args, **kwargs):
        serializer = MessageSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        return OptionalJSONResponse(result)
