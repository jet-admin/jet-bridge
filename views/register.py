from urllib.parse import quote

import tornado.web

import settings
from utils.backend import register_token


class RegisterHandler(tornado.web.RequestHandler):

    def get(self, *args, **kwargs):
        token, created = register_token()

        if not token:
            return

        url = '{}/projects/register/{}'.format(settings.JET_BACKEND_WEB_BASE_URL, token.token)
        query_string = 'referrer={}'.format(quote(self.request.full_url().encode('utf8')))
        self.redirect('%s?%s' % (url, query_string))
