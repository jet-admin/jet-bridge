from django.apps import AppConfig

from jet_bridge_base.logger import logger


class JetDjangoConfig(AppConfig):
    name = 'jet_django'

    def ready(self):
        from jet_bridge_base import configuration
        from jet_django.configuration import JetDjangoConfiguration
        conf = JetDjangoConfiguration()
        configuration.set_configuration(conf)
        from jet_bridge_base.commands.check_token import check_token_command
        check_token_command('/jet_api/')
        from jet_bridge_base.db import connect_database_from_settings

        try:
            connect_database_from_settings()
        except Exception:
            logger.exception('Database from settings connection error')
