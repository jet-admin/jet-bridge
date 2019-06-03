from jet_bridge import VERSION, settings
from jet_bridge.responses.base import Response
from jet_bridge.views.base.api import APIView


class ApiHandler(APIView):

    def get(self):
        media_url_base = settings.MEDIA_BASE_URL + '{}' if settings.MEDIA_BASE_URL \
            else self.build_absolute_uri('/media/{}')
        response = Response({
            'version': VERSION,
            'type': 'jet_bridge',
            'media_url_template': media_url_base
        })
        self.write_response(response)
