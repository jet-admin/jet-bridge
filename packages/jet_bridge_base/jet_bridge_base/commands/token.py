from jet_bridge_base.utils.backend import get_token
from jet_bridge_base.db import Session
from jet_bridge_base.logger import logger


def token_command():
    session = Session()

    try:
        token = get_token(session)

        if token:
            logger.info('Jet Admin Token:')
            logger.info(token)
        else:
            logger.info('Jet Admin Token is not set')
    finally:
        session.close()
