from django.conf import settings
from django.db import connection

from jet_bridge_base.settings import set_settings

JET_BACKEND_API_BASE_URL = getattr(settings, 'JET_BACKEND_API_BASE_URL', 'https://api.jetadmin.io/api')
JET_BACKEND_WEB_BASE_URL = getattr(settings, 'JET_BACKEND_WEB_BASE_URL', 'https://app.jetadmin.io')
JET_READ_ONLY = getattr(settings, 'JET_READ_ONLY', False)
JET_REGISTER_TOKEN_ON_START = getattr(settings, 'JET_REGISTER_TOKEN_ON_START', True)
JET_CORS_HEADERS = getattr(settings, 'JET_CORS_HEADERS', 'corsheaders' not in settings.INSTALLED_APPS)


database_settings = settings.DATABASES.get('default', {})
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
    'DEBUG': settings.DEBUG,
    'READ_ONLY': JET_READ_ONLY,
    'WEB_BASE_URL': JET_BACKEND_WEB_BASE_URL,
    'API_BASE_URL': JET_BACKEND_API_BASE_URL,
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
