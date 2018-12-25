from jet_bridge.responses.base import Response


class ListAPIViewMixin(object):

    def list(self, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(instance=page, many=True)
            response = self.get_paginated_response(serializer.representation_data)
            self.write_response(response)
            return

        serializer = self.get_serializer(instance=queryset, many=True)
        response = Response(serializer.representation_data)
        self.write_response(response)
