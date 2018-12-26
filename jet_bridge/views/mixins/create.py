from jet_bridge import status
from jet_bridge.responses.base import Response


class CreateAPIViewMixin(object):

    def create(self, *args, **kwargs):
        serializer = self.get_serializer(data=self.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        self.write_response(Response(serializer.representation_data, status=status.HTTP_201_CREATED))

    def perform_create(self, serializer):
        serializer.save()
