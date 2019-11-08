import six

from jet_bridge_base import status


class APIException(Exception):
    default_detail = 'A server error occurred.'
    default_code = 'error'
    default_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail=None, code=None, status_code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        if status_code is None:
            status_code = self.default_status_code

        self.detail = detail
        self.code = code
        self.status_code = status_code

    def __str__(self):
        return six.text_type(self.detail)
