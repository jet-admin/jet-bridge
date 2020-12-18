from sqlalchemy.exc import SQLAlchemyError

from jet_bridge_base.responses.json import JSONResponse


class ListAPIViewMixin(object):

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(request, self.get_queryset(request))

        paginate = not request.get_argument('_no_pagination', False)
        page = self.paginate_queryset(request, queryset) if paginate else None
        if page is not None:
            try:
                instance = list(page)
                serializer = self.get_serializer(request, instance=instance, many=True)
                return self.get_paginated_response(request, serializer.representation_data)
            except SQLAlchemyError:
                request.session.rollback()
                raise

        if queryset._limit is None:
            queryset = queryset.limit(10000)

        try:
            instance = list(queryset)
            serializer = self.get_serializer(request, instance=instance, many=True)
            data = serializer.representation_data
            return JSONResponse(data)
        except SQLAlchemyError:
            request.session.rollback()
            raise
