from jet_bridge_base import status
from jet_bridge_base.configuration import configuration
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.utils.exceptions import validation_error_from_database_error


class DestroyAPIViewMixin(object):

    def delete(self, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return JSONResponse(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        configuration.on_model_pre_delete(self.request.path_kwargs['model'], instance)
        self.session.delete(instance)

        try:
            self.session.commit()
        except Exception as e:
            raise validation_error_from_database_error(e, self.model)

        configuration.on_model_post_delete(self.request.path_kwargs['model'], instance)
