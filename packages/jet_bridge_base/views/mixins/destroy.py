from jet_bridge_base import status
from jet_bridge_base.responses.json import JSONResponse


class DestroyAPIViewMixin(object):

    def delete(self, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return JSONResponse(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        self.session.delete(instance)
        self.session.commit()
