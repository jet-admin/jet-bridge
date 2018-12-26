from jet_bridge import status


class ErrorDetail(object):
    code = None

    def __init__(self, string, code=None):
        self.string = string
        self.code = code

    def __eq__(self, other):
        try:
            return self.code == other.code
        except AttributeError:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return 'ErrorDetail(string=%r, code=%r)' % (
            self.string,
            self.code,
        )


def _get_error_details(data, code=None):
    if isinstance(data, list):
        ret = [
            _get_error_details(item, code) for item in data
        ]
        return ret
    elif isinstance(data, dict):
        ret = {
            key: _get_error_details(value, code) for key, value in data.items()
        }
        return ret
    else:
        text = str(data)
        code = getattr(data, 'code', code)
        return ErrorDetail(text, code)


def _get_codes(detail):
    if isinstance(detail, list):
        return [_get_codes(item) for item in detail]
    elif isinstance(detail, dict):
        return {key: _get_codes(value) for key, value in detail.items()}
    return detail.code


def _get_full_details(detail):
    if isinstance(detail, list):
        return [_get_full_details(item) for item in detail]
    elif isinstance(detail, dict):
        return {key: _get_full_details(value) for key, value in detail.items()}
    return {
        'message': detail,
        'code': detail.code
    }


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

        self.detail = _get_error_details(detail, code)
        self.code = code
        self.status_code = status_code

    def __str__(self):
        return str(self.detail)

    def get_codes(self):
        """
        Return only the code part of the error details.

        Eg. {"name": ["required"]}
        """
        return _get_codes(self.detail)

    def get_full_details(self):
        """
        Return both the message & code parts of the error details.

        Eg. {"name": [{"message": "This field is required.", "code": "required"}]}
        """
        return _get_full_details(self.detail)
