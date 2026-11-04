from jet_bridge_base import settings
from jet_bridge_base.exceptions.not_found import NotFound
from jet_bridge_base.serializers.proxy_request import ProxyRequestSerializer
from jet_bridge_base.views.base.api import BaseAPIView


class ProxyRequestView(BaseAPIView):
    serializer_class = ProxyRequestSerializer

    def get(self, request, *args, **kwargs):
        return self.make_request(request, request.query_arguments, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.make_request(request, request.data, *args, **kwargs)

    def make_request(self, request, data, *args, **kwargs):
        if not settings.PROXY_REQUEST_ENABLED:
            raise NotFound

        serializer = ProxyRequestSerializer(data=data, context={'request': request, 'handler': self})
        serializer.is_valid(raise_exception=True)
        result = serializer.submit()
        return result
