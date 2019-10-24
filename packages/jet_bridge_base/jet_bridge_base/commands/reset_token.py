from jet_bridge_base.utils.backend import reset_token
from jet_bridge_base.db import Session
from jet_bridge_base.logger import logger


def reset_token_command():
    session = Session()

    try:
        token, created = reset_token(session)

        logger.info('Token reset')

        if not created and token:
            logger.info('Token already exists: {}'.format(token.token))
        elif not created and not token:
            logger.info('Token creation failed')
        elif created and token:
            logger.info('Token created: {}'.format(token.token))
    finally:
        session.close()
