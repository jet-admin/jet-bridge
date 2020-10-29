from jet_bridge_base.responses.json import JSONResponse


class ListAPIViewMixin(object):

    def list(self, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        paginate = not self.request.get_argument('_no_pagination', False)
        page = self.paginate_queryset(queryset) if paginate else None
        if page is not None:
            serializer = self.get_serializer(instance=page, many=True)
            return self.get_paginated_response(serializer.representation_data)

        if queryset._limit is None:
            queryset = queryset.limit(10000)

        serializer = self.get_serializer(instance=queryset, many=True)
        data = serializer.representation_data
        return JSONResponse(data)
