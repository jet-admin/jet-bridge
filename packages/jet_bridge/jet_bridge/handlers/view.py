import tornado.web
from jet_bridge_base.db import get_connection
from jet_bridge_base.exceptions.request_error import RequestError
from jet_bridge_base.sentry import sentry_controller
from tornado import gen
from six.moves.urllib_parse import parse_qs

from jet_bridge_base.request import Request
from jet_bridge_base.responses.redirect import RedirectResponse
from jet_bridge_base.responses.template import TemplateResponse
from jet_bridge_base.status import HTTP_204_NO_CONTENT
from jet_bridge_base.utils.async_exec import as_future


class BaseViewHandler(tornado.web.RequestHandler):
    view = None

    def request_headers(self):
        return {k.upper().replace('-', '_'): v for k, v in self.request.headers.items()}

    def request_files(self):
        def map_file(arg):
            key, files = arg
            file = files[0]
            return key, (file.filename, file.body)

        return dict(map(map_file, self.request.files.items()))

    def get_request(self):
        query_arguments = parse_qs(self.request.query, keep_blank_values=True)
        return Request(
            self.request.method.upper(),
            self.request.protocol,
            self.request.host,
            self.request.path,
            self.path_kwargs,
            self.request.uri,
            query_arguments,
            self.request_headers(),
            self.request.body,
            self.request.body_arguments,
            self.request_files(),
            self.request,
            self
        )

    def before_dispatch(self, request):
        self.view.before_dispatch(request)

    def after_dispatch(self, request):
        self.view.after_dispatch(request)

    def on_finish(self):
        self.view.on_finish()

    def set_default_headers(self):
        for name, value in self.view.default_headers().items():
            self.set_header(name, value)

    @gen.coroutine
    def write_response(self, response):
        if isinstance(response, RedirectResponse):
            self.redirect(response.url, status=response.status)
            return

        for name, value in response.header_items():
            self.set_header(name, value)

        if response.status is not None:
            self.set_status(response.status)

        if isinstance(response, TemplateResponse):
            yield self.render(response.template, **(response.data or {}))
            return

        yield self.finish(response.render())
        raise gen.Return()

    @gen.coroutine
    def write_error(self, status_code, **kwargs):
        exc_type = exc = traceback = None

        if kwargs.get('exc_info'):
            exc_type, exc, traceback = kwargs['exc_info']
        else:
            exc = Exception()

        try:
            request = self.get_request()
        except RequestError as e:
            request = e.request

        response = self.view.error_response(request, exc_type, exc, traceback)
        yield self.write_response(response)
        raise gen.Return()

    def options(self, *args, **kwargs):
        self.set_status(HTTP_204_NO_CONTENT)
        self.finish()

    @gen.coroutine
    def dispatch(self, action, *args, **kwargs):
        request = self.get_request()

        connection = get_connection(request)
        if connection:
            sentry_controller.set_context('Database connection', {
                'name': connection.get('name'),
                'project': connection.get('project'),
                'token': connection.get('token')
            })
        else:
            sentry_controller.set_context('Database connection', {})

        def execute():
            self.before_dispatch(request)
            result = self.view.dispatch(action, request, *args, **kwargs)
            self.after_dispatch(request)
            return result

        response = yield as_future(execute)
        yield self.write_response(response)
        raise gen.Return()

    def get(self, *args, **kwargs):
        return self.dispatch('get', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.dispatch('post', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.dispatch('put', *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self.dispatch('patch', *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.dispatch('delete', *args, **kwargs)


def view_handler(cls):
    class ViewHandler(BaseViewHandler):
        view = cls()

    return ViewHandler
