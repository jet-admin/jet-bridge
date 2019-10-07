from django.conf import settings

# from jet_bridge_base.settings import set_settings

JET_BACKEND_API_BASE_URL = getattr(settings, 'JET_BACKEND_API_BASE_URL', 'https://api.jetadmin.io/api')
JET_BACKEND_WEB_BASE_URL = getattr(settings, 'JET_BACKEND_WEB_BASE_URL', 'https://app.jetadmin.io')
JET_READ_ONLY = getattr(settings, 'JET_READ_ONLY', False)
JET_REGISTER_TOKEN_ON_START = getattr(settings, 'JET_REGISTER_TOKEN_ON_START', True)
JET_CORS_HEADERS = getattr(settings, 'JET_CORS_HEADERS', 'corsheaders' not in settings.INSTALLED_APPS)

# set_settings({
#     'DEBUG': settings.DEBUG,
#     'READ_ONLY': JET_READ_ONLY,
#     'WEB_BASE_URL': JET_BACKEND_WEB_BASE_URL,
#     'API_BASE_URL': JET_BACKEND_API_BASE_URL,
#     # 'MEDIA_STORAGE': MEDIA_STORAGE,
#     # 'MEDIA_ROOT': MEDIA_ROOT,
#     # 'MEDIA_BASE_URL': MEDIA_BASE_URL,
#     'DATABASE_ENGINE': settings.DATABASE_ENGINE,
#     'DATABASE_HOST': settings.DATABASE_HOST,
#     'DATABASE_PORT': settings.DATABASE_PORT,
#     'DATABASE_USER': settings.DATABASE_USER,
#     'DATABASE_PASSWORD': settings.DATABASE_PASSWORD,
#     'DATABASE_NAME': settings.DATABASE_NAME,
#     # 'DATABASE_EXTRA': DATABASE_EXTRA,
#     # 'DATABASE_CONNECTIONS': CONNECTIONS
# })
