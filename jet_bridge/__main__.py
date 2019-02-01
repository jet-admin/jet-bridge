import os
from datetime import datetime
import webbrowser

import logging
import tornado.ioloop
import tornado.web
from requests import RequestException

import jet_bridge.adapters.postgres

from jet_bridge import settings, VERSION, media
from jet_bridge.router import Router
from jet_bridge.utils.backend import is_token_activated
from jet_bridge.views.api import ApiHandler
from jet_bridge.views.image_resize import ImageResizeHandler
from jet_bridge.views.media_file_upload import MediaFileUploadHandler
from jet_bridge.views.main import MainHandler
from jet_bridge.views.message import MessageHandler
from jet_bridge.views.model import ModelHandler
from jet_bridge.views.model_description import ModelDescriptionsHandler
from jet_bridge.views.not_found import NotFoundHandler
from jet_bridge.views.register import RegisterHandler
from jet_bridge.views.sql import SqlHandler

logging.getLogger().setLevel(logging.INFO)


def make_app():
    router = Router()

    router.register('/api/models/(?P<model>[^/]+)/', ModelHandler)

    urls = [
        (r'/', MainHandler),
        (r'/register/', RegisterHandler),
        (r'/api/', ApiHandler),
        (r'/api/register/', RegisterHandler),
        (r'/api/model_descriptions/', ModelDescriptionsHandler),
        (r'/api/sql/', SqlHandler),
        (r'/api/messages/', MessageHandler),
        (r'/api/file_upload/', MediaFileUploadHandler),
        (r'/api/image_resize/', ImageResizeHandler),
        (r'/media/(.*)', tornado.web.StaticFileHandler, {'path': settings.MEDIA_ROOT}),
    ]
    urls += router.urls

    if settings.MEDIA_STORAGE == media.MEDIA_STORAGE_DEFAULT:
        urls.append((r'/media/(.*)', tornado.web.StaticFileHandler, {'path': settings.MEDIA_ROOT}))

    return tornado.web.Application(
        handlers=urls,
        debug=settings.DEBUG,
        default_handler_class=NotFoundHandler,
        template_path=os.path.join(settings.BASE_DIR, 'templates')
    )


def main():
    app = make_app()
    app.listen(settings.PORT, settings.ADDRESS)
    address = 'localhost' if settings.ADDRESS == '0.0.0.0' else settings.ADDRESS
    url = 'http://{}:{}/'.format(address, settings.PORT)

    logging.info(datetime.now().strftime('%B %d, %Y - %H:%M:%S %Z'))
    logging.info('Jet Bridge version {}'.format(VERSION))
    logging.info('Starting server at {}'.format(url))

    if settings.DEBUG:
        logging.warning('Server is running in DEBUG mode')

    logging.info('Quit the server with CONTROL-C')

    try:
        if not is_token_activated():
            register_url = '{}register/'.format(url)
            logging.warning('[!] Your server token is not activated')

            if webbrowser.open(register_url):
                logging.warning('[!] Activation page was opened in your browser - {}'.format(register_url))
            else:
                logging.warning('[!] Go to {} to activate'.format(register_url))
    except RequestException:
        logging.error('[!] Can\'t connect to Jet Admin API')
        logging.error('[!] Token verification failed')

    tornado.ioloop.IOLoop.current().start()

if __name__ == '__main__':
    main()
