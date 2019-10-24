from six.moves.urllib import parse


def replace_query_param(url, key, val):
    (scheme, netloc, path, query, fragment) = parse.urlsplit(str(url))
    query_dict = parse.parse_qs(query, keep_blank_values=True)
    query_dict[str(key)] = [str(val)]
    query = parse.urlencode(sorted(list(query_dict.items())), doseq=True)
    return parse.urlunsplit((scheme, netloc, path, query, fragment))


def remove_query_param(url, key):
    (scheme, netloc, path, query, fragment) = parse.urlsplit(str(url))
    query_dict = parse.parse_qs(query, keep_blank_values=True)
    query_dict.pop(key, None)
    query = parse.urlencode(sorted(list(query_dict.items())), doseq=True)
    return parse.urlunsplit((scheme, netloc, path, query, fragment))
