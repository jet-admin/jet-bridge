from datetime import datetime

import tornado.ioloop
import tornado.web
import adapters.postgres
import settings
from router import Router
from version import VERSION

from views.api import ApiHandler
from views.main import MainHandler
from views.model import ModelHandler
from views.model_description import ModelDescriptionsHandler
from views.not_found import NotFoundHandler
from views.register import RegisterHandler
from views.sql import SqlHandler


def make_app():
    router = Router()

    router.register('/api/models/(?P<model>[^/]+)/', ModelHandler)

    return tornado.web.Application([
        (r'/', MainHandler),
        (r'/register/', RegisterHandler),
        (r'/api/', ApiHandler),
        (r'/api/model_descriptions/', ModelDescriptionsHandler),
        (r'/api/sql/', SqlHandler),
    ] + router.urls, debug=True, default_handler_class=NotFoundHandler)

if __name__ == '__main__':
    app = make_app()
    server = app.listen(settings.PORT, settings.ADDRESS)

    print(datetime.now().strftime('%B %d, %Y - %H:%M:%S %Z'))
    print('Jet Bridge version {}'.format(VERSION))
    print('Starting server at http://{}:{}/'.format(settings.ADDRESS, settings.PORT))
    print('Quit the server with CONTROL-C.')

    tornado.ioloop.IOLoop.current().start()
