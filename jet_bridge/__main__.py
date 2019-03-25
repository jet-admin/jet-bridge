from datetime import datetime
import webbrowser

import logging

import tornado.ioloop
import tornado.web
from requests import RequestException

import jet_bridge.adapters.postgres

from jet_bridge import settings, VERSION
from jet_bridge.settings import missing_options
from jet_bridge.utils.backend import is_token_activated
from jet_bridge.utils.create_config import create_config

logging.getLogger().setLevel(logging.INFO)


def main():
    logging.info(datetime.now().strftime('%B %d, %Y - %H:%M:%S %Z'))
    logging.info('Jet Bridge version {}'.format(VERSION))

    if missing_options == settings.required_options_without_default:
        create_config()
        return
    elif len(missing_options) and len(missing_options) < len(settings.required_options_without_default):
        logging.info('Required options are not specified: {}'.format(', '.join(missing_options)))
        return

    from jet_bridge.app import make_app

    app = make_app()
    app.listen(settings.PORT, settings.ADDRESS)
    address = 'localhost' if settings.ADDRESS == '0.0.0.0' else settings.ADDRESS
    url = 'http://{}:{}/'.format(address, settings.PORT)

    logging.info('Starting server at {}'.format(url))

    if settings.DEBUG:
        logging.warning('Server is running in DEBUG mode')

    logging.info('Quit the server with CONTROL-C')

    try:
        if not is_token_activated():
            register_url = '{}api/register/'.format(url)
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
