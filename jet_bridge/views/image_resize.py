import io
import os
from six.moves import urllib

from PIL import Image

from jet_bridge import settings
from jet_bridge.exceptions.not_found import NotFound
from jet_bridge.media_cache import cache
from jet_bridge.views.base.api import APIView


class ImageResizeHandler(APIView):

    def create_thumbnail(self, file, thumbnail_path, max_width, max_height):
        img = Image.open(file)
        img.thumbnail((max_width, max_height), Image.ANTIALIAS)

        if not os.path.exists(os.path.dirname(thumbnail_path)):
            try:
                os.makedirs(os.path.dirname(thumbnail_path))
            except OSError:
                raise

        img.save(thumbnail_path, format=img.format, quality=85)  # TODO: determine real extension from format

    def get(self):
        # TODO: Move to serializer

        path = self.get_argument('path')
        max_width = self.get_argument('max_width', 320)
        max_height = self.get_argument('max_height', 240)
        external_path = path.startswith('http://') or path.startswith('https://')
        thumbnail_full_path = cache.full_path(path)

        if not external_path:
            file = os.path.join(settings.MEDIA_ROOT, path)

            if not os.path.exists(file):
                raise NotFound
        else:
            fd = urllib.request.urlopen(path)
            file = io.BytesIO(fd.read())

        try:
            if not os.path.exists(thumbnail_full_path):
                cache.clear_cache_if_needed()
                self.create_thumbnail(file, thumbnail_full_path, max_width, max_height)
                cache.add_file(thumbnail_full_path)

            self.set_header('Content-Type', 'image/{}'.format(os.path.splitext(thumbnail_full_path)[1][1:]))

            with open(thumbnail_full_path, 'rb') as f:
                data = f.read()
                self.write(data)
            self.finish()
        except IOError as e:
            raise e
