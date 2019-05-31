import logging

from jet_bridge.utils.backend import register_token
from jet_bridge.db import Session


def register_token_command():
    try:
        session = Session()
        token, created = register_token(session)

        if not created and token:
            logging.info('Token already exists: {}'.format(token.token))
        elif not created and not token:
            logging.info('Token creation failed')
        elif created and token:
            logging.info('Token created: {}'.format(token.token))
    finally:
        session.close()
