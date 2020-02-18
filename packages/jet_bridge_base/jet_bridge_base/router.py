
def action(methods=None, detail=False):
    if methods is None:
        methods = ['get']
    else:
        methods = [method.lower() for method in methods]

    def decorator(func):
        func.bind_to_methods = methods
        func.detail = detail
        return func
    return decorator
