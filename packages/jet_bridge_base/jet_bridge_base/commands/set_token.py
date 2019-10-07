import uuid
import logging

from jet_bridge_base.utils.backend import set_token
from jet_bridge_base.db import Session


def set_token_command(token):
    try:
        session = Session()
        token = uuid.UUID(token) if token else None

        if not token:
            logging.info('No token was specified')
            return

        set_token(session, token)
    finally:
        session.close()
