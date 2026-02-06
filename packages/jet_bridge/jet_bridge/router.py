import sys
from tornado import gen

from jet_bridge.utils.async_exec import as_future


class Router(object):
    routes = [
        {
            'path': '',
            'method_mapping': {
                'get': 'list',
                'post': 'create'
            },
            'detail': False
        },
        {
            'path': 'get_records/',
            'method_mapping': {
                'post': 'list',
            },
            'detail': False
        },
        {
            'path': '(?P<pk>[^/]+)/',
            'method_mapping': {
                'get': 'retrieve',
                'put': 'update',
                'patch': 'partial_update',
                'delete': 'destroy'
            },
            'detail': True
        }
    ]
    urls = []

    def add_handler(self, view, url, actions):
        class ActionHandler(view):
            pass

        for method, method_action in actions.items():
            def create_action_method(action):
                @gen.coroutine
                def action_method(inner_self, *args, **kwargs):
                    request = inner_self.get_request()
                    request.action = action

                    def execute():
                        inner_self.before_dispatch(request)

                        try:
                            result = inner_self.view.dispatch(action, request, *args, **kwargs)
                        finally:
                            inner_self.after_dispatch(request)

                        return result

                    try:
                        response = yield as_future(execute)
                        yield inner_self.write_response(response)
                    except Exception:
                        exc_type, exc, traceback = sys.exc_info()
                        response = inner_self.view.error_response(request, exc_type, exc, traceback)
                        yield inner_self.write_response(response)
                    finally:
                        raise gen.Return()

                return action_method

            func = create_action_method(method_action)
            setattr(ActionHandler, method, func)

        self.urls.append((url, ActionHandler))

    def add_route_actions(self, view, route, prefix):
        viewset = view.view
        actions = route['method_mapping']
        actions = dict(filter(lambda x: hasattr(viewset, x[1]), actions.items()))

        if len(actions) == 0:
            return

        url = '{}{}'.format(prefix, route['path'])
        self.add_handler(view, url, actions)

    def add_route_extra_actions(self, view, route, prefix):
        viewset = view.view
        for attr in dir(viewset):
            method = getattr(viewset, attr)
            bind_to_methods = getattr(method, 'bind_to_methods', None)

            if bind_to_methods is None:
                continue

            detail = getattr(method, 'detail', None)

            if detail != route['detail']:
                continue

            extra_actions = dict(map(lambda x: (x, attr), bind_to_methods))

            url = '{}{}{}/'.format(prefix, route['path'], attr)
            self.add_handler(view, url, extra_actions)

    def register(self, prefix, view):
        for route in self.routes:
            self.add_route_extra_actions(view, route, prefix)

        for route in self.routes:
            self.add_route_actions(view, route, prefix)
