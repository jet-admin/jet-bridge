from jet_bridge_base.configuration import configuration
from jet_bridge_base.responses.json import JSONResponse


class UpdateAPIViewMixin(object):

    def update(self, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance, data=self.request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return JSONResponse(serializer.representation_data)

    def put(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def patch(self, *args, **kwargs):
        self.update(partial=True, *args, **kwargs)

    def perform_update(self, serializer):
        configuration.on_model_pre_update(self.request.path_kwargs['model'], serializer.instance)
        instance = serializer.save()
        configuration.on_model_post_update(self.request.path_kwargs['model'], instance)

    def partial_update(self, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(*args, **kwargs)
