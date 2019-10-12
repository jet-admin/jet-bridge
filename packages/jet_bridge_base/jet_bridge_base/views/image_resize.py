import io
import os

from six.moves import urllib
from PIL import Image

from jet_bridge_base import settings
from jet_bridge_base.exceptions.not_found import NotFound
from jet_bridge_base.media_cache import cache
from jet_bridge_base.responses.redirect import RedirectResponse
from jet_bridge_base.views.base.api import APIView


class ImageResizeView(APIView):

    def create_thumbnail(self, file, thumbnail_path, max_width, max_height):
        img = Image.open(file)
        img.thumbnail((max_width, max_height), Image.ANTIALIAS)

        if not os.path.exists(os.path.dirname(thumbnail_path)):
            try:
                os.makedirs(os.path.dirname(thumbnail_path))
            except OSError:
                raise

        img.save(thumbnail_path, format=img.format, quality=85)  # TODO: determine real extension from format

    def get(self, *args, **kwargs):
        # TODO: Move to serializer

        path = self.request.get_argument('path')
        max_width = self.request.get_argument('max_width', 320)
        max_height = self.request.get_argument('max_height', 240)
        external_path = path.startswith('http://') or path.startswith('https://')
        thumbnail_full_path = cache.full_path(path)

        try:
            if not os.path.exists(thumbnail_full_path):
                if not external_path:
                    file = os.path.join(settings.MEDIA_ROOT, path)

                    if not os.path.exists(file):
                        raise NotFound
                else:
                    fd = urllib.request.urlopen(path)
                    file = io.BytesIO(fd.read())

                cache.clear_cache_if_needed()
                self.create_thumbnail(file, thumbnail_full_path, max_width, max_height)
                cache.add_file(thumbnail_full_path)

            # self.set_header('Content-Type', 'image/jpg')
            #
            # with open(thumbnail_full_path, 'rb') as f:
            #     data = f.read()
            #     self.write(data)
            # self.finish()

            # self.redirect(cache.url(path))
            return RedirectResponse(cache.url(path))
        except IOError as e:
            raise e
