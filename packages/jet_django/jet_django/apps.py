import logging
from django.apps import AppConfig

import jet_django.settings

logger = logging.getLogger('jet_django')


class JetDjangoConfig(AppConfig):
    name = 'jet_django'

    def ready(self):
        from jet_bridge_base.commands.check_token import check_token_command
        check_token_command('/jet_api/')
