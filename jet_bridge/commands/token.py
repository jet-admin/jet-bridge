import logging

from jet_bridge.utils.backend import register_token, get_token
from jet_bridge.db import Session


def token_command():
    try:
        session = Session()
        token = get_token(session)

        if token:
            logging.info('Jet Admin Token:')
            logging.info(token)
        else:
            logging.info('Jet Admin Token is not set')
    finally:
        session.close()
