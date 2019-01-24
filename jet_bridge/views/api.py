from jet_bridge import VERSION
from jet_bridge.responses.base import Response
from jet_bridge.views.base.api import APIView


class ApiHandler(APIView):

    def get(self):
        response = Response({
            'version': VERSION,
            'type': 'jet_bridge',
            'media_url_template': self.build_absolute_uri('/media/{}')
        })
        self.write_response(response)
