from jet_bridge_base import status
from jet_bridge_base.exceptions.api import APIException


class MissingArgumentError(APIException):
    default_detail = 'Invalid input'
    default_code = 'invalid'
    default_status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, arg_name):
        super(MissingArgumentError, self).__init__(detail='Missing argument %s' % arg_name)
        self.arg_name = arg_name
