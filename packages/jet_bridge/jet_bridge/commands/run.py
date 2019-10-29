# import webbrowser

# from requests import RequestException

import tornado.ioloop
import tornado.web

from jet_bridge import settings
# from jet_bridge_base.utils.backend import is_token_activated, get_token, register_token
# from jet_bridge_base.db import Session
from jet_bridge_base.logger import logger


def run_command():
    from jet_bridge.app import make_app

    app = make_app()
    app.listen(settings.PORT, settings.ADDRESS)
    address = 'localhost' if settings.ADDRESS == '0.0.0.0' else settings.ADDRESS
    url = 'http://{}:{}/'.format(address, settings.PORT)

    logger.info('Starting server at {}'.format(url))

    if settings.DEBUG:
        logger.warning('Server is running in DEBUG mode')

    logger.info('Quit the server with CONTROL-C')

    # try:
    #     session = Session()
    #     token, created = register_token(session)
    #
    #     if not token:
    #         return
    #
    #     if not is_token_activated(session):
    #         token = get_token(session)
    #         register_url = '{}api/register/?token={}'.format(url, token)
    #         logger.warning('[!] Your server token is not activated')
    #         logger.warning('[!] Token: {}'.format(token))
    #         logger.warning('[!] Go to {} to activate it'.format(settings.WEB_BASE_URL))
    #
    #         if settings.AUTO_OPEN_REGISTER and webbrowser.open(register_url):
    #             logger.warning('[!] Activation page was opened in your browser - {}'.format(register_url))
    # except RequestException:
    #     logger.error('[!] Can\'t connect to Jet Admin API')
    #     logger.error('[!] Token verification failed')
    # finally:
    #     session.close()

    tornado.ioloop.IOLoop.current().start()
