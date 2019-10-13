from datetime import datetime
import logging
import sys

import tornado.ioloop
import tornado.web

from jet_bridge_base import configuration

from jet_bridge import settings
from jet_bridge.configuration import JetBridgeConfiguration

conf = JetBridgeConfiguration()
configuration.set_configuration(conf)

from jet_bridge_base.commands.check_token import check_token_command
from jet_bridge_base.utils.create_config import create_config
from jet_bridge_base import VERSION
from jet_bridge_base.db import engine_url
from jet_bridge_base.commands.register_token import register_token_command
from jet_bridge_base.commands.reset_token import reset_token_command
from jet_bridge_base.commands.set_token import set_token_command
from jet_bridge_base.commands.token import token_command

from jet_bridge.settings import missing_options, required_options_without_default


logging.getLogger().setLevel(logging.INFO)


def main():
    args = sys.argv[1:]

    logging.info(datetime.now().strftime('%B %d, %Y - %H:%M:%S %Z'))
    logging.info('Jet Bridge version {}'.format(VERSION))

    if missing_options == required_options_without_default:
        create_config()
        return
    elif len(missing_options) and len(missing_options) < len(required_options_without_default):
        logging.info('Required options are not specified: {}'.format(', '.join(missing_options)))
        return

    if not engine_url:
        raise Exception('Database configuration is not set')

    if len(args) >= 1:
        if args[0] == 'register_token':
            register_token_command()
            return
        elif args[0] == 'reset_token':
            reset_token_command()
            return
        elif args[0] == 'set_token':
            token = args[1] if len(args) >= 2 else None
            set_token_command(token)
            return
        elif args[0] == 'token':
            token_command()
            return

    from jet_bridge.app import make_app

    app = make_app()
    app.listen(settings.PORT, settings.ADDRESS)
    address = 'localhost' if settings.ADDRESS == '0.0.0.0' else settings.ADDRESS
    url = 'http://{}:{}/'.format(address, settings.PORT)
    api_url = '{}jet_api/'.format(url)

    logging.info('Starting server at {}'.format(url))

    if settings.DEBUG:
        logging.warning('Server is running in DEBUG mode')

    logging.info('Quit the server with CONTROL-C')

    check_token_command(api_url)

    tornado.ioloop.IOLoop.current().start()

if __name__ == '__main__':
    main()
