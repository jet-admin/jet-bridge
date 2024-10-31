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
from jet_bridge_base.utils.common import format_size
from jet_bridge_base.utils.conf import get_connection_name, get_conf, get_connection_schema, get_connection_id
from jet_bridge_base.utils.exceptions import serialize_validation_error


class BaseAPIView(object):
    # request = None
    # session = None
    permission_classes = []
    track_queries = False

    def log_request(self, request):
        params = {'IP': request.get_ip(), 'SID': request.get_stick_session()}
        params_str = ' '.join(map(lambda x: '='.join([x[0], x[1]]), filter(lambda x: x[1], params.items())))
        logger.debug('{} {} {}'.format(request.method, request.full_url(), params_str))

    def before_dispatch(self, request):
        self.track_query_start(request)
        self.log_request(request)

        method_override = request.headers.get('X_HTTP_METHOD_OVERRIDE')
        if method_override is not None:
            request.method = method_override

        self.before_dispatch_permissions_check(request)

    def before_dispatch_permissions_check(self, request):
        if request.method != 'OPTIONS':
            self.check_permissions(request)

    def after_dispatch(self, request):
        self.track_query_finish(request)

    def is_track_queries_enabled(self):
        return self.track_queries and (settings.TRACK_QUERY_SLOW_TIME or settings.TRACK_QUERY_HIGH_MEMORY)

    def track_query_start(self, request):
        if not self.is_track_queries_enabled():
            return

        request.start_track()

    def track_query_finish(self, request):
        if not self.is_track_queries_enabled():
            return

        track_time = request.get_track_time()
        track_memory_usage = request.get_track_memory_usage()

        tags = []

        if track_time >= settings.TRACK_QUERY_SLOW_TIME:
            tags.append('SLOW')

        if track_memory_usage >= settings.TRACK_QUERY_HIGH_MEMORY:
            tags.append('HIGHMEM')

        if not len(tags):
            return

        conf = get_conf(request)
        schema = get_connection_schema(conf)
        connection_id = get_connection_id(conf)
        connection_name = get_connection_name(conf, schema)
        id_short = connection_id[:4]

        track_query_name = self.get_track_query_name(request) or '{} {}'.format(request.method, request.path)

        logger.info('[{}] {} [{}] (MEM:{}, TIME:{}) "{}"'.format(
            id_short,
            track_query_name,
            ','.join(tags),
            format_size(track_memory_usage) if track_memory_usage else None,
            '{}s'.format(track_time),
            connection_name
        ))

    def get_track_query_name(self, request):
        pass

    def on_finish(self):
        pass

    def get_permissions(self):
        return [permission() for permission in self.permission_classes]

    def check_permissions(self, request):
        if settings.DISABLE_AUTH:
            return

        for permission in self.get_permissions():
            if not permission.has_permission(self, request):
                raise PermissionDenied(getattr(permission, 'message', 'forbidden'))

    def check_object_permissions(self, request, obj):
        if settings.DISABLE_AUTH:
            return

        for permission in self.get_permissions():
            if not permission.has_object_permission(self, request, obj):
                raise PermissionDenied(getattr(permission, 'message', 'forbidden'))

    def default_headers(self):
        headers = {}

        if settings.CORS_HEADERS:
            headers['Access-Control-Allow-Origin'] = settings.ALLOW_ORIGIN
            headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            headers['Access-Control-Allow-Headers'] = 'Authorization,DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,X-Application-Warning,X-HTTP-Method-Override,X-Bridge-Settings,X-Stick-Session'
            headers['Access-Control-Expose-Headers'] = 'Content-Length,Content-Range,Content-Disposition,Content-Type,X-Application-Warning'
            headers['Access-Control-Allow-Credentials'] = 'true'

        return headers

    def error_response(self, request, exc_type, exc, traceback):
        if isinstance(exc, PermissionDenied):
            return TemplateResponse('403.html', status=403, data={
                'path': request.path,
            })
        elif isinstance(exc, NotFound):
            return TemplateResponse('404.html', status=404, data={
                'path': request.path,
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
                    'path': request.path if request else None,
                    'full_path': request.protocol + '://' + request.host + request.path if request else None,
                    'method': request.method if request else None,
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
                logger.exception(exc)

                return TemplateResponse('500.html', status=500)

    def dispatch(self, action, request, *args, **kwargs):
        if not hasattr(self, action):
            raise NotFound()
        return getattr(self, action)(request, *args, **kwargs)

    # def build_absolute_uri(self, request, url):
    #     return request.protocol + '://' + request.host + url


class APIView(BaseAPIView):

    def before_dispatch(self, request):
        super(APIView, self).before_dispatch(request)

        try:
            request.session = create_session(request)
        except Exception as e:
            raise ValidationError(str(e))

    def after_dispatch(self, request):
        super(APIView, self).after_dispatch(request)

        if request.session is not None:
            request.session.close()
            request.session = None
