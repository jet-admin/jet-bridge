from jet_bridge_base.utils.track_database import track_database_async
from sqlalchemy.exc import SQLAlchemyError

from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.utils.queryset import get_queryset_limit


class ListAPIViewMixin(object):

    def list(self, request, *args, **kwargs):
        track_database_async(request)

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

        if get_queryset_limit(queryset) is None:
            queryset = queryset.limit(10000)

        try:
            instance = list(queryset)
            serializer = self.get_serializer(request, instance=instance, many=True)
            data = serializer.representation_data
            return JSONResponse(data)
        except SQLAlchemyError:
            request.session.rollback()
            raise
