import logging
from datetime import datetime

import sys

import jet_bridge.settings

from jet_bridge.commands.run import run_command
from jet_bridge.settings import missing_options, required_options_without_default
from jet_bridge_base.utils.create_config import create_config

from jet_bridge_base import VERSION

from jet_bridge_base.db import engine_url

from jet_bridge_base.commands.register_token import register_token_command
from jet_bridge_base.commands.reset_token import reset_token_command
from jet_bridge_base.commands.set_token import set_token_command
from jet_bridge_base.commands.token import token_command

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

    run_command()

if __name__ == '__main__':
    main()
