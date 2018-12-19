from responses.base import Response
from serializers.sql import SqlSerializer
from views.base.api import APIView


class SqlHandler(APIView):

    def post(self):
        serializer = SqlSerializer(data=self.request.body_arguments)
        serializer.is_valid(raise_exception=True)

        response = Response(serializer.execute())
        self.write_response(response)
