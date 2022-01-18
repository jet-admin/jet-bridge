import inspect


def issubclass_safe(x, A_tuple):
    return inspect.isclass(x) and issubclass(x, A_tuple)
