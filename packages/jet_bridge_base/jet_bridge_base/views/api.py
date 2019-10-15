from jet_bridge_base.configuration import configuration
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.views.base.api import APIView


class ApiView(APIView):

    def get(self, *args, **kwargs):
        return JSONResponse({
            'version': configuration.get_version(),
            'type': configuration.get_type(),
            'media_url_template': configuration.media_url('{}', self.request)
        })
