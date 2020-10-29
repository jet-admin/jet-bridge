from jet_bridge_base.responses.json import JSONResponse


class RetrieveAPIViewMixin(object):

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object(request)
        serializer = self.get_serializer(request, instance=instance)
        return JSONResponse(serializer.representation_data)
