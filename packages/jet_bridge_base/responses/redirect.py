from jet_bridge_base.responses.base import Response
from jet_bridge_base.status import HTTP_302_FOUND


class RedirectResponse(Response):

    def __init__(self, url, status=HTTP_302_FOUND):
        self.url = url
        super(RedirectResponse, self).__init__(status=status)
