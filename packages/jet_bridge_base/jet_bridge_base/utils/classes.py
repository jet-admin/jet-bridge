import inspect


def issubclass_safe(x, A_tuple):
    return inspect.isclass(x) and issubclass(x, A_tuple)


def is_instance_or_subclass(x, A_tuple):
    return isinstance(x, A_tuple) or issubclass_safe(x, A_tuple)
