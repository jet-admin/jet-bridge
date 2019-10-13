from jet_bridge_base.configuration import Configuration

from jet_bridge import settings, VERSION


class JetBridgeConfiguration(Configuration):

    def get_version(self):
        return VERSION

    def get_settings(self):
        return {
            'BRIDGE_TYPE': 'jet_bridge',
            'DEBUG': settings.DEBUG,
            'READ_ONLY': settings.READ_ONLY,
            'AUTO_OPEN_REGISTER': settings.AUTO_OPEN_REGISTER,
            'WEB_BASE_URL': settings.WEB_BASE_URL,
            'API_BASE_URL': settings.API_BASE_URL,
            'MEDIA_STORAGE': settings.MEDIA_STORAGE,
            'MEDIA_ROOT': settings.MEDIA_ROOT,
            'MEDIA_BASE_URL': settings.MEDIA_BASE_URL,
            'DATABASE_ENGINE': settings.DATABASE_ENGINE,
            'DATABASE_HOST': settings.DATABASE_HOST,
            'DATABASE_PORT': settings.DATABASE_PORT,
            'DATABASE_USER': settings.DATABASE_USER,
            'DATABASE_PASSWORD': settings.DATABASE_PASSWORD,
            'DATABASE_NAME': settings.DATABASE_NAME,
            'DATABASE_EXTRA': settings.DATABASE_EXTRA,
            'DATABASE_CONNECTIONS': settings.CONNECTIONS
        }
