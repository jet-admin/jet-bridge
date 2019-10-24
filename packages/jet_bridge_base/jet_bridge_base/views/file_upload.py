import os

from jet_bridge_base.configuration import configuration
from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.views.base.api import APIView


class FileUploadView(APIView):
    permission_classes = (HasProjectPermissions,)

    def post(self, *args, **kwargs):
        # TODO: Move to serializer
        original_filename, file = self.request.files.get('file', None)
        path = self.request.get_body_argument('path')
        filename = self.request.get_body_argument('filename', original_filename)

        upload_path = os.path.join(path, filename)
        upload_path = configuration.media_get_available_name(upload_path)

        # TODO: Add validations

        configuration.media_save(upload_path, file)

        return JSONResponse({
            'uploaded_path': upload_path,
            'uploaded_url': configuration.media_url(upload_path, self.request)
        })
