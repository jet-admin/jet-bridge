from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.serializers.sql import SqlSerializer, SqlsSerializer
from jet_bridge_base.utils.track_database import track_database_async
from jet_bridge_base.views.base.api import APIView


class SqlView(APIView):
    permission_classes = (HasProjectPermissions,)
    track_queries = True

    def post(self, request, *args, **kwargs):
        track_database_async(request)

        if 'queries' in request.data:
            serializer = SqlsSerializer(data=request.data, context={'request': request})
        else:
            serializer = SqlSerializer(data=request.data, context={'request': request})

        serializer.is_valid(raise_exception=True)
        result = serializer.execute(serializer.validated_data)
        return JSONResponse(result)
