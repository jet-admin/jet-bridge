from tornado.web import RedirectHandler


class TemporaryRedirectHandler(RedirectHandler):

    def initialize(self, url):
        super(TemporaryRedirectHandler, self).initialize(url, False)
