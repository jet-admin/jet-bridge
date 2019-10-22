import logging

from django.apps import AppConfig

logger = logging.getLogger('jet_django')


class JetDjangoConfig(AppConfig):
    name = 'jet_django'

    def ready(self):
        from jet_bridge_base import configuration
        from jet_django.configuration import JetDjangoConfiguration
        conf = JetDjangoConfiguration()
        configuration.set_configuration(conf)
        from jet_django.models.token import Token
        from jet_bridge_base.commands.check_token import check_token_command
        check_token_command('/jet_api/')
