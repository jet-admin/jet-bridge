from jet_bridge_base.responses.base import Response
from jet_bridge_base.status import HTTP_404_NOT_FOUND


class NotFoundResponse(Response):

    def __init__(self):
        super(NotFoundResponse, self).__init__(
            status=HTTP_404_NOT_FOUND,
            data='<h1>Not Found</h1><p>The requested URL {} was not found on this server.</p>'
        )
