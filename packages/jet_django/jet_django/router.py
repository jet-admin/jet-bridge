import sys
from django.conf.urls import url


class Router(object):
    routes = [
        {
            'path': '(?P<pk>[^/]+)/',
            'method_mapping': {
                'get': 'retrieve',
                'put': 'update',
                'patch': 'partial_update',
                'delete': 'destroy'
            },
            'detail': True
        },
        {
            'path': '',
            'method_mapping': {
                'get': 'list',
                'post': 'create'
            },
            'detail': False
        }
    ]
    urls = []

    def add_handler(self, view, url_, actions):
        class ActionHandler(view):
            pass

        for method, method_action in actions.items():
            def create_action_method(action):
                def action_method(inner_self, *args, **kwargs):
                    try:
                        inner_self.view.action = action
                        inner_self.before_dispatch()
                        response = inner_self.view.dispatch(action, *args, **kwargs)
                        return inner_self.write_response(response)
                    except Exception:
                        exc_type, exc, traceback = sys.exc_info()
                        response = inner_self.view.error_response(exc_type, exc, traceback)
                        return inner_self.write_response(response)
                    finally:
                        inner_self.on_finish()

                return action_method

            func = create_action_method(method_action)
            setattr(ActionHandler, method, func)

        self.urls.append(url(url_, ActionHandler.as_view()))

    def add_route_actions(self, view, route, prefix):
        viewset = view.view_cls
        actions = route['method_mapping']
        actions = dict(filter(lambda x: hasattr(viewset, x[1]), actions.items()))

        if len(actions) == 0:
            return

        url = '{}{}'.format(prefix, route['path'])
        self.add_handler(view, url, actions)

    def add_route_extra_actions(self, view, route, prefix):
        viewset = view.view_cls
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
