from jet_bridge_base.utils.track_database import track_database_async
from jet_bridge_base.utils.track_model import track_model_async
from sqlalchemy.exc import SQLAlchemyError

from jet_bridge_base import status
from jet_bridge_base.configuration import configuration
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.utils.exceptions import validation_error_from_database_error


class DestroyAPIViewMixin(object):

    def destroy(self, request, *args, **kwargs):
        track_database_async(request)

        self.apply_timezone(request)
        request.apply_rls_if_enabled()

        instance = self.get_object(request)
        self.perform_destroy(request, instance)

        serializer = self.get_serializer(request, instance=instance)
        representation_data = serializer.representation_data
        track_model_async(request, kwargs.get('model'), 'delete', kwargs.get('pk'), representation_data)

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
