from jet_bridge_base import status
from jet_bridge_base.exceptions.validation_error import ValidationError


class RequestError(ValidationError):
    default_detail = 'invalid request'
    default_code = 'invalid_request'
    default_status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(RequestError, self).__init__(*args, **kwargs)
