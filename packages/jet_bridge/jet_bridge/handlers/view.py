import platform
from datetime import datetime
import sys

import tornado.web

from jet_bridge_base import VERSION, settings, status
from jet_bridge_base.exceptions.api import APIException
from jet_bridge_base.exceptions.not_found import NotFound
from jet_bridge_base.request import Request
from jet_bridge_base.responses.redirect import RedirectResponse
from jet_bridge_base.status import HTTP_204_NO_CONTENT


class BaseViewHandler(tornado.web.RequestHandler):
    view = None

    def prepare(self):
        self.view.request = Request(
            self.request.method.upper(),
            self.request.protocol,
            self.request.host,
            self.request.path,
            self.path_kwargs,
            self.request.uri,
            self.request.query_arguments,
            self.request.headers,
            self.request.body,
            self.request.body_arguments,
            self.request.files
        )

        self.view.prepare()

        for name, value in self.view.default_headers().items():
            self.set_header(name, value)

    def on_finish(self):
        self.view.on_finish()

    def write_response(self, response):
        if isinstance(response, RedirectResponse):
            self.redirect(response.url, status=response.status)
            return

        for name, value in response.header_items():
            self.set_header(name, value)

        if response.status is not None:
            self.set_status(response.status)

        self.finish(response.render())

    def write_error(self, status_code, **kwargs):
        exc_type = exc = traceback = None

        if kwargs.get('exc_info'):
            exc_type, exc, traceback = kwargs['exc_info']

            if isinstance(exc, APIException):
                status_code = exc.status_code

        if status_code == status.HTTP_403_FORBIDDEN:
            self.render('403.html', **{
                'path': self.request.path,
            })
        elif status_code == status.HTTP_404_NOT_FOUND:
            self.render('404.html', **{
                'path': self.request.path,
            })
        else:
            if settings.DEBUG:
                ctx = {
                    'path': self.request.path,
                    'full_path': self.request.protocol + "://" + self.request.host + self.request.path,
                    'method': self.request.method,
                    'version': VERSION,
                    'current_datetime': datetime.now().strftime('%c'),
                    'python_version': platform.python_version(),
                    'python_executable': sys.executable,
                    'python_path': sys.path
                }

                if exc:
                    last_traceback = traceback

                    while last_traceback.tb_next:
                        last_traceback = last_traceback.tb_next

                    ctx.update({
                        'exception_type': exc_type.__name__,
                        'exception_value': str(exc),
                        'exception_last_traceback_line': last_traceback.tb_lineno,
                        'exception_last_traceback_name': last_traceback.tb_frame
                    })

                self.render('500.debug.html', **ctx)
            else:
                self.render('500.html')

    def options(self, *args, **kwargs):
        self.set_status(HTTP_204_NO_CONTENT)
        self.finish()

    def get(self, *args, **kwargs):
        if not hasattr(self.view, 'get'):
            raise NotFound()
        response = self.view.get(*args, **kwargs)
        self.write_response(response)

    def post(self, *args, **kwargs):
        if not hasattr(self.view, 'post'):
            raise NotFound()
        response = self.view.post(*args, **kwargs)
        self.write_response(response)

    def put(self, *args, **kwargs):
        if not hasattr(self.view, 'put'):
            raise NotFound()
        response = self.view.put(*args, **kwargs)
        self.write_response(response)

    def patch(self, *args, **kwargs):
        if not hasattr(self.view, 'patch'):
            raise NotFound()
        response = self.view.patch(*args, **kwargs)
        self.write_response(response)

    def delete(self, *args, **kwargs):
        if not hasattr(self.view, 'delete'):
            raise NotFound()
        response = self.view.delete(*args, **kwargs)
        self.write_response(response)


def view_handler(cls):
    class ViewHandler(BaseViewHandler):
        view = cls()

    return ViewHandler
