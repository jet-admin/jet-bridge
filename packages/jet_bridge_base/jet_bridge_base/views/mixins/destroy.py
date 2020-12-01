from jet_bridge_base import status
from jet_bridge_base.configuration import configuration
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.utils.exceptions import validation_error_from_database_error


class DestroyAPIViewMixin(object):

    def delete(self, request, *args, **kwargs):
        instance = self.get_object(request)
        self.perform_destroy(request, instance)
        return JSONResponse(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, request, instance):
        configuration.on_model_pre_delete(request.path_kwargs['model'], instance)
        request.session.delete(instance)

        try:
            request.session.commit()
        except Exception as e:
            request.session.rollback()
            raise validation_error_from_database_error(e, self.model)

        configuration.on_model_post_delete(request.path_kwargs['model'], instance)
