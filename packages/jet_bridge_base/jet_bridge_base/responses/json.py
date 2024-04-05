from __future__ import absolute_import
import json

from jet_bridge_base import encoders
from jet_bridge_base.responses.base import Response


class JSONResponse(Response):
    headers = {'Content-Type': 'application/json'}
    encoder_class = encoders.JSONEncoder

    def __init__(self, *args, **kwargs):
        self.rendered_data = kwargs.pop('rendered_data', None)
        super(JSONResponse, self).__init__(*args, **kwargs)

    def render(self):
        if self.rendered_data is not None:
            return self.rendered_data

        if self.data is None:
            return

        self.rendered_data = json.dumps(
            self.data,
            cls=self.encoder_class
        )
        return self.rendered_data
