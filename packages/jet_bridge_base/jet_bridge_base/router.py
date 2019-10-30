
def action(methods=list(['get']), detail=False):
    methods = [method.lower() for method in methods]

    def decorator(func):
        func.bind_to_methods = methods
        func.detail = detail
        return func
    return decorator
