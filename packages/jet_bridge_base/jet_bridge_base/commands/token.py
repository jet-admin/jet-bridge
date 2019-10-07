import logging

from jet_bridge_base.utils.backend import register_token, get_token
from jet_bridge_base.db import Session


def token_command():
    session = Session()

    try:
        token = get_token(session)

        if token:
            logging.info('Jet Admin Token:')
            logging.info(token)
        else:
            logging.info('Jet Admin Token is not set')
    finally:
        session.close()
