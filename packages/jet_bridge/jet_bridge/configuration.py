import os

from jet_bridge_base.configuration import Configuration
from jet_bridge_base.utils.common import get_random_string

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
            'DATABASE_ENGINE': settings.DATABASE_ENGINE,
            'DATABASE_HOST': settings.DATABASE_HOST,
            'DATABASE_PORT': settings.DATABASE_PORT,
            'DATABASE_USER': settings.DATABASE_USER,
            'DATABASE_PASSWORD': settings.DATABASE_PASSWORD,
            'DATABASE_NAME': settings.DATABASE_NAME,
            'DATABASE_EXTRA': settings.DATABASE_EXTRA,
            'DATABASE_CONNECTIONS': settings.CONNECTIONS
        }

    def media_get_available_name(self, path):
        dir_name, file_name = os.path.split(path)
        file_root, file_ext = os.path.splitext(file_name)

        while os.path.exists(os.path.join(settings.MEDIA_ROOT, path)):
            path = os.path.join(dir_name, '%s_%s%s' % (file_root, get_random_string(7), file_ext))

        return path

    def media_save(self, path, content):
        absolute_path = os.path.join(settings.MEDIA_ROOT, path)

        if not os.path.exists(os.path.dirname(absolute_path)):
            try:
                os.makedirs(os.path.dirname(absolute_path))
            except OSError:
                raise

        with open(absolute_path, 'wb') as f:
            f.write(content)

        return path

    def media_url(self, path, request):
        url = '/media/{}'.format(path)
        return request.protocol + "://" + request.host + url
