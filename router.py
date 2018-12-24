
class Router(object):
    routes = [
        {
            'path': '',
            'method_mapping': {
                'get': 'list',
                'post': 'create'
            },
        },
        {
            'path': '(?P<id>[^/]+)/',
            'method_mapping': {
                'get': 'retrieve',
                'put': 'update',
                'patch': 'partial_update',
                'delete': 'destroy'
            }
        }
    ]
    urls = []

    def register(self, prefix, viewset):
        for route in self.routes:
            actions = route['method_mapping']
            actions = dict(filter(lambda x: hasattr(viewset, x[1]), actions.items()))

            if len(actions) == 0:
                continue

            class ActionHandler(viewset):
                pass

            for method, method_action in actions.items():
                def create_action_method(action):
                    def action_method(inner_self, *args, **kwargs):
                        return getattr(inner_self, action)(*args, **kwargs)
                    return action_method

                func = create_action_method(method_action)
                setattr(ActionHandler, method, func)

            url = '{}{}'.format(prefix, route['path'])
            self.urls.append((url, ActionHandler))
