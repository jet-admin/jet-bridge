from responses.base import Response


class RetrieveAPIViewMixin(object):

    def get(self, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance)
        self.write_response(Response(serializer.representation_data))
