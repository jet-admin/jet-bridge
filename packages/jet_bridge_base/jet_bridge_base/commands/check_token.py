import webbrowser

from requests import RequestException

from jet_bridge_base import settings
from jet_bridge_base.utils.backend import is_token_activated
from jet_bridge_base.logger import logger


def check_token_command(api_url):
    try:
        if not is_token_activated(settings.TOKEN):
            logger.warning('[!] Your server token is not activated')
            logger.warning('[!] Token: {}'.format(settings.TOKEN))

            if settings.AUTO_OPEN_REGISTER and api_url.startswith('http'):
                register_url = '{}register/'.format(api_url)

                if settings.TOKEN:
                    register_url += '?token={}'.format(settings.TOKEN)

                if webbrowser.open(register_url):
                    logger.warning('[!] Activation page was opened in your browser - {}'.format(register_url))
            else:
                register_url = '{}register/'.format(api_url)
                logger.warning('[!] Go to {} to activate it'.format(register_url))
    except RequestException:
        logger.error('[!] Can\'t connect to Jet Admin API')
        logger.error('[!] Token verification failed')
