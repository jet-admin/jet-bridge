import os

from jet_bridge_base import settings
from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.utils.common import get_random_string
from jet_bridge_base.views.base.api import APIView


class FileUploadView(APIView):
    permission_classes = (HasProjectPermissions,)

    def get_available_name(self, name):
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)

        while os.path.exists(name):
            name = os.path.join(dir_name, '%s_%s%s' % (file_root, get_random_string(7), file_ext))

        return name

    def post(self):
        # TODO: Move to serializer
        file = self.request.files.get('file', [])[0]
        path = self.request.data.get('path')
        filename = self.request.data.get('filename', file.filename)

        upload_path = os.path.join(settings.MEDIA_ROOT, path, filename)
        upload_path = self.get_available_name(upload_path)

        relative_upload_path = upload_path[len(settings.MEDIA_ROOT) + 1:]

        # TODO: Add validations

        if not os.path.exists(os.path.dirname(upload_path)):
            try:
                os.makedirs(os.path.dirname(upload_path))
            except OSError:
                raise

        with open(upload_path, 'wb') as f:
            f.write(file['body'])

        return JSONResponse({
            'uploaded_path': relative_upload_path,
            'uploaded_url': self.build_absolute_uri('/media/{}'.format(relative_upload_path))
        })
