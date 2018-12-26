from datetime import datetime

import tornado.ioloop
import tornado.web
import jet_bridge.adapters.postgres

from jet_bridge import settings, VERSION
from jet_bridge.router import Router
from jet_bridge.utils.backend import is_token_activated
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
    ] + router.urls, debug=settings.DEBUG, default_handler_class=NotFoundHandler)


def main():
    app = make_app()
    app.listen(settings.PORT, settings.ADDRESS)
    address = 'localhost' if settings.ADDRESS == '0.0.0.0' else settings.ADDRESS
    url = 'http://{}:{}/'.format(address, settings.PORT)

    print(datetime.now().strftime('%B %d, %Y - %H:%M:%S %Z'))
    print('Jet Bridge version {}'.format(VERSION))
    print('Starting server at {}'.format(url))

    if settings.DEBUG:
        print('Server is running in DEBUG mode')

    print('Quit the server with CONTROL-C')

    if not is_token_activated():
        print('[!] Your server token is not activated')
        print('[!] Go to {}register/ to activate'.format(url))

    tornado.ioloop.IOLoop.current().start()

if __name__ == '__main__':
    main()
