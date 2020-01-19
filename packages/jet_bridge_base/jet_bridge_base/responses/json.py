from __future__ import absolute_import
import json

from jet_bridge_base import encoders
from jet_bridge_base.responses.base import Response


class JSONResponse(Response):
    headers = {'Content-Type': 'application/json'}
    encoder_class = encoders.JSONEncoder

    def render(self):
        if self.data is None:
            return

        return json.dumps(
            self.data,
            cls=self.encoder_class
        )
