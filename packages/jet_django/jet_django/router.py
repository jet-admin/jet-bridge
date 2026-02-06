import sys


class Router(object):
    routes = [
        {
            'path': 'get_records',
            'regex': 'get_records',
            'method_mapping': {
                'post': 'list',
            },
            'detail': False
        },
        {
            'path': '<pk>/',
            'regex': '(?P<pk>[^/]+)/',
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
            'regex': '',
            'method_mapping': {
                'get': 'list',
                'post': 'create'
            },
            'detail': False
        }
    ]
    urls = []

    def add_handler(self, view, path_, regex, actions):
        class ActionHandler(view):
            pass

        for method, method_action in actions.items():
            def create_action_method(action):
                def action_method(inner_self, *args, **kwargs):
                    request = inner_self.get_request()
                    request.action = action

                    try:
                        inner_self.view.action = action
                        inner_self.before_dispatch(request)
                        response = inner_self.view.dispatch(action, request, *args, **kwargs)
                        return inner_self.write_response(response)
                    except Exception:
                        exc_type, exc, traceback = sys.exc_info()
                        response = inner_self.view.error_response(request, exc_type, exc, traceback)
                        return inner_self.write_response(response)
                    finally:
                        inner_self.on_finish(request)

                return action_method

            func = create_action_method(method_action)
            setattr(ActionHandler, method, func)

        try:
            from django.urls import path
            self.urls.append(path(path_, ActionHandler.as_view()))
        except ImportError:
            from django.conf.urls import url
            self.urls.append(url(regex, ActionHandler.as_view()))

    def add_route_actions(self, view, route, prefix_path, prefix_regex):
        viewset = view.view_cls
        actions = route['method_mapping']
        actions = dict(filter(lambda x: hasattr(viewset, x[1]), actions.items()))

        if len(actions) == 0:
            return

        path = '{}{}'.format(prefix_path, route['path'])
        regex = '{}{}'.format(prefix_regex, route['regex'])
        self.add_handler(view, path, regex, actions)

    def add_route_extra_actions(self, view, route, prefix_path, prefix_regex):
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

            path = '{}{}{}/'.format(prefix_path, route['path'], attr)
            regex = '{}{}{}/'.format(prefix_regex, route['regex'], attr)
            self.add_handler(view, path, regex, extra_actions)

    def register(self, prefix_path, prefix_regex, view):
        for route in self.routes:
            self.add_route_extra_actions(view, route, prefix_path, prefix_regex)

        for route in self.routes:
            self.add_route_actions(view, route, prefix_path, prefix_regex)
