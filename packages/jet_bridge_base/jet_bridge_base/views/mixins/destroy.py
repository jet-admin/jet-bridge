from jet_bridge_base.utils.track import track_database_async
from sqlalchemy.exc import SQLAlchemyError

from jet_bridge_base import status
from jet_bridge_base.configuration import configuration
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.utils.exceptions import validation_error_from_database_error


class DestroyAPIViewMixin(object):

    def delete(self, request, *args, **kwargs):
        track_database_async(request)

        instance = self.get_object(request)
        self.perform_destroy(request, instance)
        return JSONResponse(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, request, instance):
        configuration.on_model_pre_delete(request.path_kwargs['model'], instance)
        Model = self.get_model(request)
        request.session.delete(instance)

        try:
            request.session.commit()
        except SQLAlchemyError as e:
            request.session.rollback()
            raise validation_error_from_database_error(e, Model)

        configuration.on_model_post_delete(request.path_kwargs['model'], instance)
