from jet_bridge_base.db import Session
from jet_bridge_base.exceptions.not_found import NotFound
from jet_bridge_base.exceptions.permission_denied import PermissionDenied
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.responses.json import JSONResponse


class APIView(object):
    request = None
    session = None
    permission_classes = []

    def prepare(self):
        method_override = self.request.headers.get('X_HTTP_METHOD_OVERRIDE')
        if method_override is not None:
            self.request.method = method_override

        if self.request.method != 'OPTIONS':
            self.check_permissions()

        self.session = Session()

    def on_finish(self):
        if self.session:
            self.session.close()
            self.session = None

    def get_permissions(self):
        return [permission() for permission in self.permission_classes]

    def check_permissions(self):
        for permission in self.get_permissions():
            if not permission.has_permission(self):
                raise PermissionDenied(getattr(permission, 'message', 'forbidden'))

    def check_object_permissions(self, obj):
        for permission in self.get_permissions():
            if not permission.has_object_permission(self, obj):
                raise PermissionDenied(getattr(permission, 'message', 'forbidden'))

    def default_headers(self):
        ACCESS_CONTROL_ALLOW_ORIGIN = 'Access-Control-Allow-Origin'
        ACCESS_CONTROL_EXPOSE_HEADERS = 'Access-Control-Expose-Headers'
        ACCESS_CONTROL_ALLOW_CREDENTIALS = 'Access-Control-Allow-Credentials'
        ACCESS_CONTROL_ALLOW_HEADERS = 'Access-Control-Allow-Headers'
        ACCESS_CONTROL_ALLOW_METHODS = 'Access-Control-Allow-Methods'

        return {
            ACCESS_CONTROL_ALLOW_ORIGIN: '*',
            ACCESS_CONTROL_ALLOW_METHODS: 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
            ACCESS_CONTROL_ALLOW_HEADERS: 'Authorization,DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,X-Application-Warning,X-HTTP-Method-Override',
            ACCESS_CONTROL_EXPOSE_HEADERS: 'Content-Length,Content-Range,Content-Disposition,Content-Type,X-Application-Warning',
            ACCESS_CONTROL_ALLOW_CREDENTIALS: 'true'
        }

    def handle_exception(self, exc):
        if isinstance(exc, ValidationError):
            return JSONResponse({
                'error': True,
                'exc': type(exc).__name__
            })

        raise exc

    def dispatch(self, action, *args, **kwargs):
        if not hasattr(self, action):
            raise NotFound()
        try:
            return getattr(self, action)(*args, **kwargs)
        except Exception as e:
            return self.handle_exception(e)

    def build_absolute_uri(self, url):
        return self.request.protocol + "://" + self.request.host + url
