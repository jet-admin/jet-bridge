from jet_bridge_base import status
from jet_bridge_base.configuration import configuration
from jet_bridge_base.responses.json import JSONResponse


class DestroyAPIViewMixin(object):

    def delete(self, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return JSONResponse(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        configuration.on_model_pre_delete(self.request.path_kwargs['model'], instance)
        self.session.delete(instance)
        self.session.commit()
        configuration.on_model_post_delete(self.request.path_kwargs['model'], instance)
