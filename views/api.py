from responses.base import Response
from version import VERSION
from views.base.api import APIView


class ApiHandler(APIView):

    def get(self):
        response = Response({
            'version': VERSION,
            'type': 'jet_bridge'
        })
        self.write_response(response)
