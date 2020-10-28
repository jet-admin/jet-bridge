from tornado import gen

from jet_bridge_base.configuration import configuration
from jet_bridge_base.responses.json import JSONResponse


class UpdateAPIViewMixin(object):

    @gen.coroutine
    def update(self, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = yield self.get_object()
        serializer = self.get_serializer(instance=instance, data=self.request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        yield self.perform_update(serializer)
        return JSONResponse(serializer.representation_data)

    @gen.coroutine
    def put(self, *args, **kwargs):
        yield self.update(*args, **kwargs)

    @gen.coroutine
    def patch(self, *args, **kwargs):
        yield self.update(partial=True, *args, **kwargs)

    @gen.coroutine
    def perform_update(self, serializer):
        configuration.on_model_pre_update(self.request.path_kwargs['model'], serializer.instance)
        instance = yield serializer.save()
        configuration.on_model_post_update(self.request.path_kwargs['model'], instance)

    def partial_update(self, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(*args, **kwargs)
