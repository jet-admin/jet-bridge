import status
from exceptions.api import APIException


class ValidationError(APIException):
    default_detail = 'Invalid input'
    default_code = 'invalid'
    default_status_code = status.HTTP_400_BAD_REQUEST
