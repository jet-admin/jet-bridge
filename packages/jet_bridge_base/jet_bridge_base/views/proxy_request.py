from jet_bridge_base.serializers.proxy_request import ProxyRequestSerializer
from jet_bridge_base.views.base.api import BaseAPIView


class ProxyRequestView(BaseAPIView):
    serializer_class = ProxyRequestSerializer

    def get(self, *args, **kwargs):
        return self.make_request(self.request.query_arguments, *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.make_request(self.request.data, *args, **kwargs)

    def make_request(self, data, *args, **kwargs):
        serializer = ProxyRequestSerializer(data=data, context={'request': self.request, 'handler': self})
        serializer.is_valid(raise_exception=True)
        result = serializer.submit()
        return result
