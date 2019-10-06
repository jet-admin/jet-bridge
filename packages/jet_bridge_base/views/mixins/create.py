from jet_bridge_base import status
from jet_bridge_base.responses.json import JSONResponse


class CreateAPIViewMixin(object):

    def create(self, *args, **kwargs):
        serializer = self.get_serializer(data=self.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return JSONResponse(serializer.representation_data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save()
