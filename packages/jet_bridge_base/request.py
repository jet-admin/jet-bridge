import json

from jet_bridge_base.exceptions.missing_argument_error import MissingArgumentError

_ARG_DEFAULT = object()


class Request(object):

    def __init__(self, method, protocol, host, path, path_kwargs, uri, query_arguments, headers, body, body_arguments, files):
        self.method = method
        self.protocol = protocol
        self.host = host
        self.path = path
        self.path_kwargs = path_kwargs
        self.uri = uri
        self.query_arguments = query_arguments
        self.headers = headers
        self.body = body
        self.body_arguments = body_arguments
        self.files = files or {}

        content_type = self.headers.get('Content-Type', '')

        if content_type.startswith('application/json'):
            self.data = json.loads(self.body)
        else:
            self.data = self.body_arguments

    def full_url(self):
        return self.protocol + "://" + self.host + self.uri

    def get_argument(self, name, default=_ARG_DEFAULT, strip=True):
        return self._get_argument(name, default, self.query_arguments, strip)

    def get_arguments(self, name, strip=True):
        return self._get_arguments(name, self.query_arguments, strip)

    def get_body_argument(self, name, default=_ARG_DEFAULT, strip=True):
        return self._get_argument(name, default, self.body_arguments, strip)

    def get_body_arguments(self, name, strip=True):
        return self._get_arguments(name, self.body_arguments, strip)

    def _get_argument(self, name, default, source, strip=True):
        args = self._get_arguments(name, source, strip=strip)
        if not args:
            if default is _ARG_DEFAULT:
                raise MissingArgumentError(name)
            return default
        return args[-1]

    def _get_arguments(self, name, source, strip=True):
        values = []
        for v in source.get(name, []):
            v = v.decode('utf-8')
            # v = self.decode_argument(v, name=name)
            # if isinstance(v, unicode_type):
            #     # Get rid of any weird control chars (unless decoding gave
            #     # us bytes, in which case leave it alone)
            #     v = RequestHandler._remove_control_chars_regex.sub(" ", v)
            if strip:
                v = v.strip()
            values.append(v)
        return values
