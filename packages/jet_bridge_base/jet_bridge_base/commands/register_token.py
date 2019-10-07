import logging

from jet_bridge_base.utils.backend import register_token
from jet_bridge_base.db import Session


def register_token_command():
    session = Session()

    try:
        token, created = register_token(session)

        if not created and token:
            logging.info('Token already exists: {}'.format(token.token))
        elif not created and not token:
            logging.info('Token creation failed')
        elif created and token:
            logging.info('Token created: {}'.format(token.token))
    finally:
        session.close()
