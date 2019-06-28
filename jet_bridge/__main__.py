import logging

import sys

from jet_bridge.commands.register_token import register_token_command
from jet_bridge.commands.reset_token import reset_token_command
from jet_bridge.commands.run import run_command
from jet_bridge.commands.set_token import set_token_command
from jet_bridge.commands.token import token_command

logging.getLogger().setLevel(logging.INFO)


def main():
    args = sys.argv[1:]

    if len(args) >= 1:
        if args[0] == 'register_token':
            register_token_command()
            return
        elif args[0] == 'reset_token':
            reset_token_command()
            return
        elif args[0] == 'set_token':
            set_token_command(args)
            return
        elif args[0] == 'token':
            token_command()
            return

    run_command()

if __name__ == '__main__':
    main()
