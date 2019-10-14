import io
from six.moves import urllib
from PIL import Image

from jet_bridge_base.configuration import configuration
from jet_bridge_base.exceptions.not_found import NotFound
from jet_bridge_base.media_cache import cache
from jet_bridge_base.responses.redirect import RedirectResponse
from jet_bridge_base.views.base.api import APIView


class ImageResizeView(APIView):

    def create_thumbnail(self, file, thumbnail_path, max_width, max_height):
        img = Image.open(file)
        img.thumbnail((max_width, max_height), Image.ANTIALIAS)

        with io.BytesIO() as memory_file:
            img.save(memory_file, format=img.format, quality=85)  # TODO: determine real extension from format
            memory_file.seek(0)
            configuration.media_save(thumbnail_path, memory_file.read())

    def get(self, *args, **kwargs):
        # TODO: Move to serializer
        # TODO: Add options dependant cache name

        path = self.request.get_argument('path')
        max_width = self.request.get_argument('max_width', 320)
        max_height = self.request.get_argument('max_height', 240)
        external_path = path.startswith('http://') or path.startswith('https://')

        try:
            if not cache.exists(path):
                thumbnail_full_path = cache.full_path(path)

                if not external_path:
                    if not configuration.media_exists(path):
                        raise NotFound

                    file = configuration.media_open(path)
                else:
                    fd = urllib.request.urlopen(path)
                    file = io.BytesIO(fd.read())

                with file:
                    cache.clear_cache_if_needed()
                    self.create_thumbnail(file, thumbnail_full_path, max_width, max_height)
                    cache.add_file(path)

            # self.set_header('Content-Type', 'image/jpg')
            #
            # with open(thumbnail_full_path, 'rb') as f:
            #     data = f.read()
            #     self.write(data)
            # self.finish()

            # self.redirect(cache.url(path))
            return RedirectResponse(cache.url(path, self.request))
        except IOError as e:
            raise e
