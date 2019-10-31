import json

from jet_bridge_base.exceptions.missing_argument_error import MissingArgumentError

_ARG_DEFAULT = object()


class Request(object):

    def __init__(
            self,
            method=None,
            protocol=None,
            host=None,
            path=None,
            path_kwargs=None,
            uri=None,
            query_arguments=None,
            headers=None,
            body=None,
            body_arguments=None,
            files=None
    ):
        self.method = method
        self.protocol = protocol
        self.host = host
        self.path = path
        self.path_kwargs = path_kwargs
        self.uri = uri
        self.query_arguments = query_arguments or {}
        self.headers = headers or {}
        self.body = body
        self.body_arguments = body_arguments or {}
        self.files = files or {}

        content_type = self.headers.get('CONTENT_TYPE', '')

        if content_type.startswith('application/json'):
            data = self.body

            if not isinstance(data, str):
                data = data.decode('utf-8', 'surrogatepass')

            self.data = json.loads(data) if data else {}
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
            if isinstance(v, bytes):
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
