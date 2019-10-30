
class Response(object):
    headers = {'Content-Type': 'text/html'}

    def __init__(self, data=None, status=None, headers=None, exception=False, content_type=None):
        self.data = data
        self.status = status
        self.exception = exception
        self.content_type = content_type

        if headers:
            self.headers.update(headers)

    def header_items(self):
        if not self.headers:
            return []
        return self.headers.items()

    def render(self):
        if self.data is None:
            return bytes()

        return self.data
