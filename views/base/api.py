import tornado.web


class APIView(tornado.web.RequestHandler):

    def set_default_headers(self):
        ACCESS_CONTROL_ALLOW_ORIGIN = 'Access-Control-Allow-Origin'
        ACCESS_CONTROL_EXPOSE_HEADERS = 'Access-Control-Expose-Headers'
        ACCESS_CONTROL_ALLOW_CREDENTIALS = 'Access-Control-Allow-Credentials'
        ACCESS_CONTROL_ALLOW_HEADERS = 'Access-Control-Allow-Headers'
        ACCESS_CONTROL_ALLOW_METHODS = 'Access-Control-Allow-Methods'

        self.set_header(ACCESS_CONTROL_ALLOW_ORIGIN, '*')
        self.set_header(ACCESS_CONTROL_ALLOW_METHODS, 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        self.set_header(ACCESS_CONTROL_ALLOW_HEADERS, 'Authorization,DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,X-Application-Warning')
        self.set_header(ACCESS_CONTROL_EXPOSE_HEADERS, 'Content-Length,Content-Range,X-Application-Warning')
        self.set_header(ACCESS_CONTROL_ALLOW_CREDENTIALS, 'true')

    def options(self, *args, **kwargs):
        self.set_status(204)
        self.finish()

    def write_response(self, response):
        for name, value in response.header_items():
            self.set_header(name, value)
        self.write(response.render())
