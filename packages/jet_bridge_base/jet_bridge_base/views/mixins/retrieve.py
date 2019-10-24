from jet_bridge_base.responses.json import JSONResponse


class RetrieveAPIViewMixin(object):

    def retrieve(self, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance)
        return JSONResponse(serializer.representation_data)
