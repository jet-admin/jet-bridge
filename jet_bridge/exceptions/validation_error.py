from jet_bridge import status
from jet_bridge.exceptions.api import APIException


class ValidationError(APIException):
    default_detail = 'Invalid input'
    default_code = 'invalid'
    default_status_code = status.HTTP_400_BAD_REQUEST
