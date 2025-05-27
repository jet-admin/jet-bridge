import json

from django.conf import settings
from django.db import connection

from jet_bridge_base.logger import logger
from jet_bridge_base.settings import DEFAULT_CONFIG_PATH

JET_READ_ONLY = getattr(settings, 'JET_READ_ONLY', False)
JET_AUTO_OPEN_REGISTER = getattr(settings, 'JET_AUTO_OPEN_REGISTER', True)
JET_CONFIG = getattr(settings, 'JET_CONFIG', DEFAULT_CONFIG_PATH)
JET_PROJECT = getattr(settings, 'JET_PROJECT', None)
JET_TOKEN = getattr(settings, 'JET_TOKEN', None)
JET_ENVIRONMENT = getattr(settings, 'JET_ENVIRONMENT', None)
JET_CORS_HEADERS = getattr(settings, 'JET_CORS_HEADERS', 'corsheaders' not in settings.INSTALLED_APPS)
JET_BASE_URL = getattr(settings, 'JET_BASE_URL', None)
JET_JWT_VERIFY_KEY = getattr(settings, 'JET_JWT_VERIFY_KEY', None)
JET_BEARER_AUTH_KEY = getattr(settings, 'JET_BEARER_AUTH_KEY', None)
JET_ENVIRONMENT_TYPE = getattr(settings, 'JET_ENVIRONMENT_TYPE', 'django')
JET_BLACKLIST_HOSTS = getattr(settings, 'JET_BLACKLIST_HOSTS', None)

JET_BACKEND_API_BASE_URL = getattr(settings, 'JET_BACKEND_API_BASE_URL', 'https://api.jetadmin.io/api')
JET_BACKEND_WEB_BASE_URL = getattr(settings, 'JET_BACKEND_WEB_BASE_URL', 'https://app.jetadmin.io')

try:
    from django.conf import DEFAULT_STORAGE_ALIAS
    DJANGO_DEFAULT_FILE_STORAGE = DEFAULT_STORAGE_ALIAS
except ImportError:
    DJANGO_DEFAULT_FILE_STORAGE = settings.DEFAULT_FILE_STORAGE

JET_MEDIA_FILE_STORAGE = getattr(settings, 'JET_MEDIA_FILE_STORAGE', DJANGO_DEFAULT_FILE_STORAGE)

JET_DJANGO_DATABASE = getattr(settings, 'JET_DJANGO_DATABASE', 'default')
JET_DATABASE_EXTRA = getattr(settings, 'JET_DATABASE_EXTRA', None)
JET_DATABASE_ONLY = getattr(settings, 'JET_DATABASE_ONLY', None)
JET_DATABASE_EXCEPT = getattr(settings, 'JET_DATABASE_EXCEPT', None)
JET_DATABASE_MAX_TABLES = getattr(settings, 'JET_DATABASE_MAX_TABLES', None)
JET_DATABASE_SCHEMA = getattr(settings, 'JET_DATABASE_SCHEMA', None)
JET_DATABASE_TIMEZONE = getattr(settings, 'JET_DATABASE_TIMEZONE', None)
JET_DATABASE_RLS_TYPE = getattr(settings, 'JET_DATABASE_RLS_TYPE', None)
JET_DATABASE_RLS_SSO = getattr(settings, 'JET_DATABASE_RLS_SSO', None)
JET_DATABASE_RLS_USER_PROPERTY = getattr(settings, 'JET_DATABASE_RLS_USER_PROPERTY', None)
JET_DATABASE_REFLECT_MAX_RECORDS = getattr(settings, 'JET_DATABASE_REFLECT_MAX_RECORDS', 1000000)

JET_DATABASE_SSL_CA = getattr(settings, 'JET_DATABASE_SSL_CA', None)
JET_DATABASE_SSL_CERT = getattr(settings, 'JET_DATABASE_SSL_CERT', None)
JET_DATABASE_SSL_KEY = getattr(settings, 'JET_DATABASE_SSL_KEY', None)

JET_DATABASE_SSH_HOST = getattr(settings, 'JET_DATABASE_SSH_HOST', None)
JET_DATABASE_SSH_PORT = getattr(settings, 'JET_DATABASE_SSH_PORT', None)
JET_DATABASE_SSH_USER = getattr(settings, 'JET_DATABASE_SSH_USER', None)
JET_DATABASE_SSH_PRIVATE_KEY = getattr(settings, 'JET_DATABASE_SSH_PRIVATE_KEY', None)

JET_COOKIE_SAMESITE = getattr(settings, 'JET_COOKIE_SAMESITE', 'None')
JET_COOKIE_SECURE = getattr(settings, 'JET_COOKIE_SECURE', True)
JET_COOKIE_DOMAIN = getattr(settings, 'JET_COOKIE_DOMAIN', None)
JET_COOKIE_COMPRESS = getattr(settings, 'JET_COOKIE_COMPRESS', False)

JET_STORE_PATH = getattr(settings, 'JET_STORE_PATH', 'jet_bridge_store.sqlite3')

JET_CACHE_METADATA = getattr(settings, 'JET_CACHE_METADATA', False)
JET_CACHE_METADATA_PATH = getattr(settings, 'JET_CACHE_METADATA_PATH', 'metadata')
JET_CACHE_MODEL_DESCRIPTIONS = getattr(settings, 'JET_CACHE_MODEL_DESCRIPTIONS', False)

JET_SSO_APPLICATIONS = getattr(settings, 'JET_SSO_APPLICATIONS', '{}')
JET_ALLOW_ORIGIN = getattr(settings, 'JET_ALLOW_ORIGIN', '*')

JET_TRACK_DATABASES = getattr(settings, 'JET_TRACK_DATABASES', '')
JET_TRACK_DATABASES_ENDPOINT = getattr(settings, 'JET_TRACK_DATABASES_ENDPOINT', '')
JET_TRACK_DATABASES_AUTH = getattr(settings, 'JET_TRACK_DATABASES_AUTH', '')

JET_TRACK_MODELS_ENDPOINT = getattr(settings, 'JET_TRACK_MODELS_ENDPOINT', '')
JET_TRACK_MODELS_AUTH = getattr(settings, 'JET_TRACK_MODELS_AUTH', '')

JET_TRACK_QUERY_SLOW_TIME = getattr(settings, 'JET_TRACK_QUERY_SLOW_TIME', None)
JET_TRACK_QUERY_HIGH_MEMORY = getattr(settings, 'JET_TRACK_QUERY_HIGH_MEMORY', None)

JET_DISABLE_AUTH = getattr(settings, 'JET_DISABLE_AUTH', False)

try:
    JET_SSO_APPLICATIONS = json.loads(JET_SSO_APPLICATIONS)
except Exception as e:
    logger.error('SSO_APPLICATIONS parsing failed', exc_info=e)
    JET_SSO_APPLICATIONS = {}

database_settings = settings.DATABASES.get(JET_DJANGO_DATABASE, {})
database_engine = None

mysql_read_default_file = database_settings.get('OPTIONS', {}).get('read_default_file')

if JET_DATABASE_EXTRA is None and mysql_read_default_file:
    JET_DATABASE_EXTRA = '?read_default_file={}'.format(mysql_read_default_file)

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
