import platform
from datetime import datetime
import sys

import six

from jet_bridge_base import settings
from jet_bridge_base.configuration import configuration
from jet_bridge_base.db import create_session
from jet_bridge_base.exceptions.api import APIException
from jet_bridge_base.exceptions.not_found import NotFound
from jet_bridge_base.exceptions.permission_denied import PermissionDenied
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.responses.template import TemplateResponse
from jet_bridge_base.logger import logger
from jet_bridge_base.utils.exceptions import serialize_validation_error


class BaseAPIView(object):
    request = None
    session = None
    permission_classes = []

    def before_dispatch(self):
        method_override = self.request.headers.get('X_HTTP_METHOD_OVERRIDE')
        if method_override is not None:
            self.request.method = method_override

        if self.request.method != 'OPTIONS':
            self.check_permissions()

    def on_finish(self):
        pass

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
        headers = {}

        if settings.CORS_HEADERS:
            headers['Access-Control-Allow-Origin'] = '*'
            headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            headers['Access-Control-Allow-Headers'] = 'Authorization,DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,X-Application-Warning,X-HTTP-Method-Override,X-Bridge-Settings'
            headers['Access-Control-Expose-Headers'] = 'Content-Length,Content-Range,Content-Disposition,Content-Type,X-Application-Warning'
            headers['Access-Control-Allow-Credentials'] = 'true'

        return headers

    def error_response(self, exc_type, exc, traceback):
        if isinstance(exc, PermissionDenied):
            return TemplateResponse('403.html', status=403, data={
                'path': self.request.path,
            })
        elif isinstance(exc, NotFound):
            return TemplateResponse('404.html', status=404, data={
                'path': self.request.path,
            })
        elif isinstance(exc, ValidationError):
            response = serialize_validation_error(exc)
            return JSONResponse(response, status=exc.status_code)
        elif isinstance(exc, APIException):
            return JSONResponse({
                'error': exc.detail,
                'error_code': exc.code
            }, status=exc.status_code)
        else:
            if settings.DEBUG:
                ctx = {
                    'path': self.request.path if self.request else None,
                    'full_path': self.request.protocol + '://' + self.request.host + self.request.path if self.request else None,
                    'method': self.request.method if self.request else None,
                    'type': configuration.get_type(),
                    'version': configuration.get_version(),
                    'current_datetime': datetime.now().strftime('%c'),
                    'python_version': platform.python_version(),
                    'python_executable': sys.executable,
                    'python_path': sys.path
                }

                if exc:
                    ctx.update({
                        'exception_type': exc_type.__name__,
                        'exception_value': six.text_type(exc)
                    })

                if traceback:
                    last_traceback = traceback

                    while last_traceback.tb_next:
                        last_traceback = last_traceback.tb_next

                    frame = last_traceback.tb_frame
                    func_name = frame.f_code.co_name
                    file_name = frame.f_code.co_filename
                    line_number = frame.f_lineno

                    ctx.update({
                        'exception_last_traceback_line': line_number,
                        'exception_last_traceback_func': func_name,
                        'exception_last_traceback_file': file_name,
                    })

                logger.exception(exc)

                return TemplateResponse('500.debug.html', status=500, data=ctx)
            else:
                return TemplateResponse('500.html', status=500)

    def dispatch(self, action, *args, **kwargs):
        if not hasattr(self, action):
            raise NotFound()
        return getattr(self, action)(*args, **kwargs)

    def build_absolute_uri(self, url):
        return self.request.protocol + "://" + self.request.host + url


class APIView(BaseAPIView):
    request = None
    session = None
    permission_classes = []

    def before_dispatch(self):
        super(APIView, self).before_dispatch()

        try:
            self.session = create_session(self.request)
        except Exception as e:
            raise ValidationError(str(e))

    def on_finish(self):
        super(APIView, self).on_finish()

        if self.session:
            self.session.close()
            self.session = None
