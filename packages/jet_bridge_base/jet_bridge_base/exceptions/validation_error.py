from jet_bridge_base import status
from jet_bridge_base.exceptions.api import APIException


class ValidationError(APIException):
    default_detail = 'invalid input'
    default_code = 'invalid'
    default_status_code = status.HTTP_400_BAD_REQUEST
