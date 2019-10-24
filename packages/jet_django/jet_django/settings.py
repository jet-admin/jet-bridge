from django.conf import settings
from django.db import connection

JET_BACKEND_API_BASE_URL = getattr(settings, 'JET_BACKEND_API_BASE_URL', 'https://api.jetadmin.io/api')
JET_BACKEND_WEB_BASE_URL = getattr(settings, 'JET_BACKEND_WEB_BASE_URL', 'https://app.jetadmin.io')
JET_READ_ONLY = getattr(settings, 'JET_READ_ONLY', False)
JET_REGISTER_TOKEN_ON_START = getattr(settings, 'JET_REGISTER_TOKEN_ON_START', True)
JET_CORS_HEADERS = getattr(settings, 'JET_CORS_HEADERS', 'corsheaders' not in settings.INSTALLED_APPS)
JET_MEDIA_FILE_STORAGE = getattr(settings, 'JET_MEDIA_FILE_STORAGE', settings.DEFAULT_FILE_STORAGE)


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
