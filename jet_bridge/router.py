
def action(methods=list(['get']), detail=False):
    methods = [method.lower() for method in methods]

    def decorator(func):
        func.bind_to_methods = methods
        func.detail = detail
        return func
    return decorator


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

    def add_handler(self, viewset, url, actions):
        class ActionHandler(viewset):
            pass

        for method, method_action in actions.items():
            def create_action_method(action):
                def action_method(inner_self, *args, **kwargs):
                    inner_self.action = action
                    return getattr(inner_self, action)(*args, **kwargs)

                return action_method

            func = create_action_method(method_action)
            setattr(ActionHandler, method, func)

        self.urls.append((url, ActionHandler))

    def add_route_actions(self, viewset, route, prefix):
        actions = route['method_mapping']
        actions = dict(filter(lambda x: hasattr(viewset, x[1]), actions.items()))

        if len(actions) == 0:
            return

        url = '{}{}'.format(prefix, route['path'])
        self.add_handler(viewset, url, actions)

    def add_route_extra_actions(self, viewset, route, prefix):
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
            self.add_handler(viewset, url, extra_actions)

    def register(self, prefix, viewset):
        for route in self.routes:
            self.add_route_extra_actions(viewset, route, prefix)
            self.add_route_actions(viewset, route, prefix)
