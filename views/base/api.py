import tornado.web

from paginators.page_number import PageNumberPagination


class APIView(tornado.web.RequestHandler):
    serializer_class = None
    filter_class = None
    pagination_class = PageNumberPagination
    _paginator = None
    args = []
    kwargs = {}

    def set_default_headers(self):
        ACCESS_CONTROL_ALLOW_ORIGIN = 'Access-Control-Allow-Origin'
        ACCESS_CONTROL_EXPOSE_HEADERS = 'Access-Control-Expose-Headers'
        ACCESS_CONTROL_ALLOW_CREDENTIALS = 'Access-Control-Allow-Credentials'
        ACCESS_CONTROL_ALLOW_HEADERS = 'Access-Control-Allow-Headers'
        ACCESS_CONTROL_ALLOW_METHODS = 'Access-Control-Allow-Methods'

        self.set_header(ACCESS_CONTROL_ALLOW_ORIGIN, '*')
        self.set_header(ACCESS_CONTROL_ALLOW_METHODS, 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        self.set_header(ACCESS_CONTROL_ALLOW_HEADERS, 'Authorization,DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,X-Application-Warning')
        self.set_header(ACCESS_CONTROL_EXPOSE_HEADERS, 'Content-Length,Content-Range,X-Application-Warning')
        self.set_header(ACCESS_CONTROL_ALLOW_CREDENTIALS, 'true')

    def get_queryset(self):
        raise NotImplementedError

    def get_filter(self, *args, **kwargs):
        filter_class = self.get_filter_class()
        if not filter_class:
            return
        kwargs['context'] = self.filter_context()
        return filter_class(*args, **kwargs)

    def get_filter_class(self):
        return self.filter_class

    def filter_context(self):
        return {
            'request': self.request,
            'handler': self
        }

    def filter_queryset(self, queryset):
        filter_instance = self.get_filter()
        if filter_instance:
            queryset = filter_instance.filter_queryset(queryset)
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
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(queryset, self)

    def get_paginated_response(self, data):
        assert self.paginator is not None
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

    def options(self):
        self.set_status(204)
        self.finish()

    def write_response(self, response):
        for name, value in response.header_items():
            self.set_header(name, value)
        self.write(response.render())
