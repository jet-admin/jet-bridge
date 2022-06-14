from jet_bridge_base import status
from jet_bridge_base.configuration import configuration
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.utils.track import track_database_async


class CreateAPIViewMixin(object):

    def create(self, request, *args, **kwargs):
        track_database_async(request)

        serializer = self.get_serializer(request, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(request, serializer)
        return JSONResponse(serializer.representation_data, status=status.HTTP_201_CREATED)

    def perform_create(self, request, serializer):
        serializer_instance = serializer.create_instance(serializer.validated_data)
        configuration.on_model_pre_create(request.path_kwargs['model'], serializer_instance)
        instance = serializer.save()
        configuration.on_model_post_create(request.path_kwargs['model'], instance)
