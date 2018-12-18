import tornado.web

from paginators.page_number import PageNumberPagination
from responses import Response


class APIView(tornado.web.RequestHandler):
    serializer_class = None
    pagination_class = PageNumberPagination
    _paginator = None
    args = []
    kwargs = {}

    def get_queryset(self):
        raise NotImplementedError

    def filter_queryset(self, queryset):
        return queryset

    @property
    def paginator(self):
        if not self._paginator:
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset):
        return self.paginator.paginate_queryset(queryset, self)

    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)

    def get_serializer_class(self):
        return self.serializer_class

    def get_serializer_context(self):
        return {
            'request': self.request,
            'view': self
        }

    def write_response(self, response):
        for name, value in response.header_items():
            self.set_header(name, value)
        self.write(response.render())


class CreateAPIViewMixin(object):

    def post(self, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.representation_data)
        self.write_response(Response(serializer.representation_data, status=status.HTTP_201_CREATED, headers=headers))

    def perform_create(self, serializer):
        serializer.save()

    def get_success_headers(self, data):
        try:
            return {'Location': str(data[api_settings.URL_FIELD_NAME])}
        except (TypeError, KeyError):
            return {}


class ListAPIViewMixin(object):

    def get(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

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


class RetrieveAPIViewMixin(object):

    def get(self, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance)
        self.write_response(Response(serializer.representation_data))


class UpdateAPIViewMixin(object):

    def update(self, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        self.write_response(Response(serializer.representation_data))

    def put(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def patch(self, *args, **kwargs):
        self.update(partial=True, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save()


class DestroyAPIViewMixin(object):

    def delete(self, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        self.write_response(Response(status=status.HTTP_204_NO_CONTENT))

    def perform_destroy(self, instance):
        instance.delete()
