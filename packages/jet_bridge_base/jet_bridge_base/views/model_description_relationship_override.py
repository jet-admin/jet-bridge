from jet_bridge_base.serializers.relationship_override import ModelDescriptionRelationOverridesSerializer

from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.views.base.api import APIView


class ModelDescriptionRelationshipOverrideView(APIView):
    permission_classes = (HasProjectPermissions,)

    def post(self, request, *args, **kwargs):
        serializer_context = {'request': request}
        serializer = ModelDescriptionRelationOverridesSerializer(data=request.data, many=True, context=serializer_context)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return JSONResponse(serializer.representation_data)
