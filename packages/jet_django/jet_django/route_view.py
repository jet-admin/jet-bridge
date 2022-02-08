import os
import sys
from django.http import HttpResponse, HttpResponseRedirect
from django.http.response import HttpResponseBase
from django.template import Template
from django.template.context import Context
from django.views import generic
from django.views.decorators.csrf import csrf_exempt

from jet_bridge_base import settings as base_settings
from jet_bridge_base.exceptions.request_error import RequestError
from jet_bridge_base.request import Request
from jet_bridge_base.responses.base import Response
from jet_bridge_base.responses.optional_json import OptionalJSONResponse
from jet_bridge_base.responses.redirect import RedirectResponse
from jet_bridge_base.responses.template import TemplateResponse

from jet_bridge_base.status import HTTP_204_NO_CONTENT


class BaseRouteView(generic.View):
    view_cls = None
    view = None

    def request_headers(self):
        def filter_header_key(k):
            return k.startswith('HTTP_') or k in ['CONTENT_LENGTH', 'CONTENT_TYPE']

        def map_header_key(k):
            return k[len('HTTP_'):] if k.startswith('HTTP_') else k

        return {map_header_key(k): v for k, v in self.request.META.items() if filter_header_key(k)}

    def request_files(self):
        def map_file(arg):
            key, file = arg
            return key, (file.name, file.file)

        return dict(map(map_file, self.request.FILES.dict().items()))

    def get_request(self):
        return Request(
            self.request.method.upper(),
            self.request.scheme,
            self.request.get_host(),
            self.request.path,
            self.kwargs,
            self.request.get_full_path(),
            dict(self.request.GET.lists()),
            self.request_headers(),
            self.request.body,
            dict(self.request.POST.lists()),
            self.request_files(),
            self
        )

    def before_dispatch(self, request):
        self.view = self.view_cls()
        self.view.before_dispatch(request)

    def on_finish(self, request):
        self.view.after_dispatch(request)
        self.view.on_finish()

    def write_response(self, response):
        if isinstance(response, RedirectResponse):
            result = HttpResponseRedirect(response.url, status=response.status)
        elif isinstance(response, OptionalJSONResponse) and isinstance(response.data, HttpResponseBase):
            result = response.data
        elif isinstance(response, TemplateResponse):
            template_path = os.path.join(base_settings.BASE_DIR, 'templates', response.template)
            with open(template_path, 'r') as file:
                template = file.read()
                template = template.replace('{% end %}', '{% endif %}')
                context = Context(response.data)
                content = Template(template).render(context)
                result = HttpResponse(content, status=response.status)
        else:
            result = HttpResponse(response.render(), status=response.status)

        for name, value in self.view.default_headers().items():
            result[name] = value

        for name, value in response.header_items():
            result[name] = value

        return result

    def options(self, request, *args, **kwargs):
        return self.write_response(Response(status=HTTP_204_NO_CONTENT))

    def get(self, *args, **kwargs):
        response = self.view.dispatch('get', *args, **kwargs)
        return self.write_response(response)

    def post(self, *args, **kwargs):
        response = self.view.dispatch('post', *args, **kwargs)
        return self.write_response(response)

    def put(self, *args, **kwargs):
        response = self.view.dispatch('put', *args, **kwargs)
        return self.write_response(response)

    def patch(self, *args, **kwargs):
        response = self.view.dispatch('patch', *args, **kwargs)
        return self.write_response(response)

    def delete(self, *args, **kwargs):
        response = self.view.dispatch('delete', *args, **kwargs)
        return self.write_response(response)

    def dispatch(self, original_request, *args, **kwargs):
        try:
            request = self.get_request()
        except RequestError as e:
            request = e.request

        try:
            self.before_dispatch(request)
            response = super(BaseRouteView, self).dispatch(request, *args, **kwargs)
            return response
        except Exception:
            exc_type, exc, traceback = sys.exc_info()
            response = self.view.error_response(request, exc_type, exc, traceback)
            return self.write_response(response)
        finally:
            self.on_finish(request)

    @classmethod
    def as_view(cls, **initkwargs):
        view = super(BaseRouteView, cls).as_view(**initkwargs)
        view.cls = cls
        view.initkwargs = initkwargs
        return csrf_exempt(view)


def route_view(cls):
    class RouteView(BaseRouteView):
        view_cls = cls

    return RouteView
