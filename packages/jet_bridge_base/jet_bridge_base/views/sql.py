from jet_bridge_base.exceptions.sql import SqlError
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.serializers.sql import SqlSerializer, SqlsSerializer
from jet_bridge_base.utils.track import track_database_async
from jet_bridge_base.views.base.api import APIView
from jet_bridge_base.status import HTTP_400_BAD_REQUEST


class SqlView(APIView):
    permission_classes = (HasProjectPermissions,)

    def post(self, request, *args, **kwargs):
        track_database_async(request)

        if 'queries' in request.data:
            serializer = SqlsSerializer(data=request.data, context={'request': request})
        else:
            serializer = SqlSerializer(data=request.data, context={'request': request})

        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            return JSONResponse({'error': str(e)}, status=HTTP_400_BAD_REQUEST)

        try:
            result = serializer.execute(serializer.validated_data)
            return JSONResponse(result)
        except SqlError as e:
            return JSONResponse({'error': str(e.detail)}, status=HTTP_400_BAD_REQUEST)
