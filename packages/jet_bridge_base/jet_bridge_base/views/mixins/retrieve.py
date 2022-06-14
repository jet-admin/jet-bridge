from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.utils.track import track_database_async


class RetrieveAPIViewMixin(object):

    def retrieve(self, request, *args, **kwargs):
        track_database_async(request)

        instance = self.get_object(request)
        serializer = self.get_serializer(request, instance=instance)
        return JSONResponse(serializer.representation_data)
