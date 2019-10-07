from jet_bridge_base import status
from jet_bridge_base.exceptions.api import APIException


class NotFound(APIException):
    default_detail = 'Not Found'
    default_code = 'not_found'
    default_status_code = status.HTTP_404_NOT_FOUND
