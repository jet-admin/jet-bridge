import uuid

from jet_bridge_base.utils.backend import set_token
from jet_bridge_base.db import Session
from jet_bridge_base.logger import logger


def set_token_command(token):
    session = Session()

    try:
        token = uuid.UUID(token) if token else None

        if not token:
            logger.info('No token was specified')
            return

        set_token(session, token)
    finally:
        session.close()
