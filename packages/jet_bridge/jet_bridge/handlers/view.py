import tornado.web

from jet_bridge_base.request import Request
from jet_bridge_base.responses.redirect import RedirectResponse
from jet_bridge_base.responses.template import TemplateResponse
from jet_bridge_base.status import HTTP_204_NO_CONTENT


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

    def before_dispatch(self):
        self.view.request = Request(
            self.request.method.upper(),
            self.request.protocol,
            self.request.host,
            self.request.path,
            self.path_kwargs,
            self.request.uri,
            self.request.query_arguments,
            self.request_headers(),
            self.request.body,
            self.request.body_arguments,
            self.request_files()
        )

        self.view.before_dispatch()

    def on_finish(self):
        self.view.on_finish()

    def set_default_headers(self):
        for name, value in self.view.default_headers().items():
            self.set_header(name, value)

    def write_response(self, response):
        if isinstance(response, RedirectResponse):
            self.redirect(response.url, status=response.status)
            return

        for name, value in response.header_items():
            self.set_header(name, value)

        if response.status is not None:
            self.set_status(response.status)

        if isinstance(response, TemplateResponse):
            self.render(response.template, **(response.data or {}))
            return

        self.finish(response.render())

    def write_error(self, status_code, **kwargs):
        exc_type = exc = traceback = None

        if kwargs.get('exc_info'):
            exc_type, exc, traceback = kwargs['exc_info']
        else:
            exc = Exception()

        response = self.view.error_response(exc_type, exc, traceback)
        self.write_response(response)

    def options(self, *args, **kwargs):
        self.set_status(HTTP_204_NO_CONTENT)
        self.finish()

    def get(self, *args, **kwargs):
        self.before_dispatch()
        response = self.view.dispatch('get', *args, **kwargs)
        self.write_response(response)

    def post(self, *args, **kwargs):
        self.before_dispatch()
        response = self.view.dispatch('post', *args, **kwargs)
        self.write_response(response)

    def put(self, *args, **kwargs):
        self.before_dispatch()
        response = self.view.dispatch('put', *args, **kwargs)
        self.write_response(response)

    def patch(self, *args, **kwargs):
        self.before_dispatch()
        response = self.view.dispatch('patch', *args, **kwargs)
        self.write_response(response)

    def delete(self, *args, **kwargs):
        self.before_dispatch()
        response = self.view.dispatch('delete', *args, **kwargs)
        self.write_response(response)


def view_handler(cls):
    class ViewHandler(BaseViewHandler):
        view = cls()

    return ViewHandler
