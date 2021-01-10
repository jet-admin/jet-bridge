import os

from jet_bridge_base.configuration import Configuration
from jet_bridge_base.utils.common import get_random_string

from jet_bridge import settings, VERSION

from six.moves.http_cookies import Morsel

Morsel._reserved[str('samesite')] = str('SameSite')


class JetBridgeConfiguration(Configuration):

    def get_type(self):
        return 'jet_bridge'

    def get_version(self):
        return VERSION

    def get_settings(self):
        return {
            'DEBUG': settings.DEBUG,
            'READ_ONLY': settings.READ_ONLY,
            'AUTO_OPEN_REGISTER': settings.AUTO_OPEN_REGISTER,
            'WEB_BASE_URL': settings.WEB_BASE_URL,
            'API_BASE_URL': settings.API_BASE_URL,
            'PROJECT': settings.PROJECT,
            'TOKEN': settings.TOKEN,
            'CORS_HEADERS': settings.CORS_HEADERS,
            'BASE_URL': settings.BASE_URL,
            'JWT_VERIFY_KEY': settings.JWT_VERIFY_KEY,
            'ENVIRONMENT_TYPE': settings.ENVIRONMENT_TYPE,
            'DATABASE_ENGINE': settings.DATABASE_ENGINE,
            'DATABASE_HOST': settings.DATABASE_HOST,
            'DATABASE_PORT': settings.DATABASE_PORT,
            'DATABASE_USER': settings.DATABASE_USER,
            'DATABASE_PASSWORD': settings.DATABASE_PASSWORD,
            'DATABASE_NAME': settings.DATABASE_NAME,
            'DATABASE_EXTRA': settings.DATABASE_EXTRA,
            'DATABASE_CONNECTIONS': settings.CONNECTIONS,
            'DATABASE_ONLY': settings.DATABASE_ONLY,
            'DATABASE_EXCEPT': settings.DATABASE_EXCEPT,
            'DATABASE_SCHEMA': settings.DATABASE_SCHEMA,
            'SSO_APPLICATIONS': self.clean_sso_applications(settings.SSO_APPLICATIONS),
            'ALLOW_ORIGIN': settings.ALLOW_ORIGIN
        }

    def media_get_available_name(self, path):
        dir_name, file_name = os.path.split(path)
        file_root, file_ext = os.path.splitext(file_name)

        while os.path.exists(os.path.join(settings.MEDIA_ROOT, path)):
            path = os.path.join(dir_name, '%s_%s%s' % (file_root, get_random_string(7), file_ext))

        return path

    def media_exists(self, path):
        absolute_path = os.path.join(settings.MEDIA_ROOT, path)
        return os.path.exists(absolute_path)

    def media_listdir(self, path):
        absolute_path = os.path.join(settings.MEDIA_ROOT, path)
        directories = []
        files = []

        for dirpath, dirnames, filenames in os.walk(absolute_path):
            directories.extend(dirnames)
            files.extend(filenames)

        return directories, files

    def media_get_modified_time(self, path):
        absolute_path = os.path.join(settings.MEDIA_ROOT, path)
        return os.path.getmtime(absolute_path)

    def media_size(self, path):
        absolute_path = os.path.join(settings.MEDIA_ROOT, path)
        return os.path.getsize(absolute_path)

    def media_open(self, path, mode='rb'):
        return open(path, mode)

    def media_save(self, path, content):
        absolute_path = os.path.join(settings.MEDIA_ROOT, path)

        if not os.path.exists(os.path.dirname(absolute_path)):
            try:
                os.makedirs(os.path.dirname(absolute_path))
            except OSError:
                pass

        with open(absolute_path, 'wb') as f:
            f.write(content)

        return path

    def media_delete(self, path):
        absolute_path = os.path.join(settings.MEDIA_ROOT, path)
        os.remove(absolute_path)

    def media_url(self, path, request):
        if settings.MEDIA_BASE_URL:
            url = '{}{}'.format(settings.MEDIA_BASE_URL, path)
        else:
            url = request.protocol + "://" + request.host + '/media/' + path

        return url

    def session_get(self, request, name, default=None):
        value = request.original_handler.get_secure_cookie(name)
        if value is None:
            return default
        else:
            return value.decode()

    def session_set(self, request, name, value):
        if value is None:
            self.session_clear(request, name)
        else:
            request.original_handler.set_secure_cookie(name, value, samesite='None', secure=True)

    def session_clear(self, request, name):
        request.original_handler.clear_cookie(name)
