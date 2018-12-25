from datetime import datetime

import tornado.ioloop
import tornado.web
import jet_bridge.adapters.postgres

from jet_bridge import settings, VERSION
from jet_bridge.router import Router
from jet_bridge.views.api import ApiHandler
from jet_bridge.views.main import MainHandler
from jet_bridge.views.message import MessageHandler
from jet_bridge.views.model import ModelHandler
from jet_bridge.views.model_description import ModelDescriptionsHandler
from jet_bridge.views.not_found import NotFoundHandler
from jet_bridge.views.register import RegisterHandler
from jet_bridge.views.sql import SqlHandler


def make_app():
    router = Router()

    router.register('/api/models/(?P<model>[^/]+)/', ModelHandler)

    return tornado.web.Application([
        (r'/', MainHandler),
        (r'/register/', RegisterHandler),
        (r'/api/', ApiHandler),
        (r'/api/register/', RegisterHandler),
        (r'/api/model_descriptions/', ModelDescriptionsHandler),
        (r'/api/sql/', SqlHandler),
        (r'/api/messages/', MessageHandler),
    ] + router.urls, debug=True, default_handler_class=NotFoundHandler)


def main():
    app = make_app()
    app.listen(settings.PORT, settings.ADDRESS)

    print(datetime.now().strftime('%B %d, %Y - %H:%M:%S %Z'))
    print('Jet Bridge version {}'.format(VERSION))
    print('Starting server at http://{}:{}/'.format(settings.ADDRESS, settings.PORT))
    print('Quit the server with CONTROL-C.')

    tornado.ioloop.IOLoop.current().start()

if __name__ == '__main__':
    main()
