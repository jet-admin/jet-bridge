import tornado.web
from tornado.escape import json_decode


class APIView(tornado.web.RequestHandler):
    permission_classes = []

    @property
    def data(self):
        content_type = self.request.headers.get('Content-Type', '')
        if content_type.startswith('application/json'):
            return json_decode(self.request.body)
        else:
            return self.request.body_arguments

    def prepare(self):
        if self.request.method != 'OPTIONS':
            self.check_permissions()

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

    def get_permissions(self):
        return [permission() for permission in self.permission_classes]

    def check_permissions(self):
        for permission in self.get_permissions():
            if not permission.has_permission(self):
                raise Exception(getattr(permission, 'message', None))

    def check_object_permissions(self, obj):
        for permission in self.get_permissions():
            if not permission.has_object_permission(self, obj):
                raise Exception(getattr(permission, 'message', None))

    def options(self, *args, **kwargs):
        self.set_status(204)
        self.finish()

    def write_response(self, response):
        for name, value in response.header_items():
            self.set_header(name, value)
        self.write(response.render())

    def write_error(self, status_code, **kwargs):
        print(kwargs.get('exc_info'))
        self.write('Error %s' % status_code)
