from jet_bridge import status
from jet_bridge.responses.base import Response


class DestroyAPIViewMixin(object):

    def delete(self, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        self.write_response(Response(status=status.HTTP_204_NO_CONTENT))

    def perform_destroy(self, instance):
        self.session.delete(instance)
        self.session.commit()
