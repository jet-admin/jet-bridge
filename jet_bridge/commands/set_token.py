import uuid
import logging

from jet_bridge.utils.backend import set_token
from jet_bridge.db import Session


def set_token_command(args):
    try:
        session = Session()
        token = uuid.UUID(args[1]) if len(args) >= 2 else None

        if not token:
            logging.info('No token was specified')
            return

        set_token(session, token)
    finally:
        session.close()
