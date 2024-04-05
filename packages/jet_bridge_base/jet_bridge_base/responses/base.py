
class Response(object):
    def __init__(self, data=None, status=None, headers=None, exception=False, content_type=None):
        self.data = data
        self.status = status
        self.exception = exception
        self.content_type = content_type
        self.headers = self.default_headers()

        if headers:
            self.headers.update(headers)

    def default_headers(self):
        return {'Content-Type': 'text/html'}

    def header_items(self):
        if not self.headers:
            return []
        return self.headers.items()

    def render(self):
        return self.data
