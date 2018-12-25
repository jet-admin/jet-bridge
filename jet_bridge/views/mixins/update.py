from jet_bridge.responses.base import Response


class UpdateAPIViewMixin(object):

    def update(self, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance, data=self.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        self.write_response(Response(serializer.representation_data))

    def put(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def patch(self, *args, **kwargs):
        self.update(partial=True, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save()
