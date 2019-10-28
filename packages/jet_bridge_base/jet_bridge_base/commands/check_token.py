import webbrowser

from requests import RequestException

from jet_bridge_base import settings
from jet_bridge_base.utils.backend import is_token_activated, get_token, register_token
from jet_bridge_base.db import Session
from jet_bridge_base.logger import logger


def check_token_command(api_url):
    session = Session()

    try:
        # token, created = register_token(session)

        # if not token:
        #     return

        if not is_token_activated(session):
            # token = get_token(session)

            logger.warning('[!] Your server token is not activated')
            # logger.warning('[!] Token: {}'.format(token))

            register_url = '{}register/'.format(api_url)

            if settings.AUTO_OPEN_REGISTER and api_url.startswith('http'):
                # register_url = '{}register/?token={}'.format(api_url, token)

                if webbrowser.open(register_url):
                    logger.warning('[!] Activation page was opened in your browser - {}'.format(register_url))
            else:
                # register_url = '{}register/'.format(api_url)
                logger.warning('[!] Go to {} to activate it'.format(register_url))
    except RequestException:
        logger.error('[!] Can\'t connect to Jet Admin API')
        logger.error('[!] Token verification failed')
    finally:
        session.close()
