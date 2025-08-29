from jet_bridge_base import status
from jet_bridge_base.exceptions.api import APIException


class SqlError(APIException):
    default_detail = 'Query failed'
    default_code = 'query_failed'
    default_status_code = status.HTTP_400_BAD_REQUEST
