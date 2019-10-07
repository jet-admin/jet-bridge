import logging

# import sys
from django.apps import AppConfig
from django.conf import settings as django_settings
from django.db import connection
# from django.apps import apps
# from django.db import ProgrammingError
#
from jet_bridge_base.settings import set_settings

from jet_django import settings

logger = logging.getLogger('jet_django')


class JetDjangoConfig(AppConfig):
    name = 'jet_django'

    # def check_token(self):
    #     from jet_django.utils.backend import register_token, is_token_activated
    #
    #     is_command = len(sys.argv) > 1 and sys.argv[1].startswith('jet_')
    #
    #     if not is_command and settings.JET_REGISTER_TOKEN_ON_START:
    #         try:
    #             print('[JET] Checking if token is not activated yet...')
    #             token, created = register_token()
    #
    #             if not token:
    #                 return
    #
    #             if not is_token_activated(token):
    #                 print('[!] Your server token is not activated')
    #                 print('[!] Token: {}'.format(token.token))
    #             else:
    #                 print('[JET] Token activated')
    #         except ProgrammingError as e:
    #             no_migrations = str(e).find('relation "jet_django_token" does not exist') != -1
    #             if no_migrations:
    #                 print('[JET] Apply migrations first: python manage.py migrate jet_django')
    #             else:
    #                 print(e)
    #         except Exception as e:  # if no migrations yet
    #             print(e)
    #             pass
    #
    # def register_models(self):
    #     from jet_django.admin.jet import jet
    #
    #     try:
    #         models = apps.get_models()
    #
    #         for model in models:
    #             jet.register(model)
    #     except:  # if no migrations yet
    #         pass

    def ready(self):
        pass
        # self.check_token()
        # self.register_models()

        database_settings = django_settings.DATABASES.get('default', {})
        database_engine = None

        if connection.vendor == 'postgresql':
            database_engine = 'postgresql'
        elif connection.vendor == 'mysql':
            database_engine = 'mysql'
        elif connection.vendor == 'oracle':
            database_engine = 'oracle'
        elif connection.vendor in ('mssql', 'microsoft'):
            database_engine = 'mssql+pyodbc'
        elif connection.vendor == 'sqlite':
            database_engine = 'sqlite'

        set_settings({
            'DEBUG': django_settings.DEBUG,
            'READ_ONLY': settings.JET_READ_ONLY,
            'WEB_BASE_URL': settings.JET_BACKEND_WEB_BASE_URL,
            'API_BASE_URL': settings.JET_BACKEND_API_BASE_URL,
            # 'MEDIA_STORAGE': MEDIA_STORAGE,
            # 'MEDIA_ROOT': MEDIA_ROOT,
            # 'MEDIA_BASE_URL': MEDIA_BASE_URL,
            'DATABASE_ENGINE': database_engine,
            'DATABASE_HOST': database_settings.get('HOST'),
            'DATABASE_PORT': database_settings.get('PORT'),
            'DATABASE_USER': database_settings.get('USER'),
            'DATABASE_PASSWORD': database_settings.get('PASSWORD'),
            'DATABASE_NAME': database_settings.get('NAME'),
            # 'DATABASE_EXTRA': DATABASE_EXTRA,
            'DATABASE_CONNECTIONS': 1
        })

