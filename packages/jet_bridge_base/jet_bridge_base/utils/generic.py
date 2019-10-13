

# TODO: Fix non dict list items
def merge(destination, source):
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            merge(node, value)
        elif isinstance(value, list):
            node = destination.setdefault(key, [])
            for i, item in enumerate(value):
                merge(node[i], value[i])
        else:
            destination[key] = value

    return destination
