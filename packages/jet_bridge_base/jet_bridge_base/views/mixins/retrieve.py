from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.utils.track_database import track_database_async


class RetrieveAPIViewMixin(object):

    def retrieve(self, request, *args, **kwargs):
        track_database_async(request)

        self.apply_timezone(request)
        request.apply_rls_if_enabled()
        instance = self.get_object(request)
        serializer = self.get_serializer(request, instance=instance)
        return JSONResponse(serializer.representation_data)
