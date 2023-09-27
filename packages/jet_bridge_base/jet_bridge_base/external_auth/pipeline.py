import json
import time

from jet_bridge_base import settings
from jet_bridge_base.configuration import configuration
from jet_bridge_base.external_auth.storage import User
from jet_bridge_base.utils.compress import compress_data


def save_extra_data(backend, user, response, details, strategy, *args, **kwargs):
    extra_data = backend.extra_data(user, 0, response, details, *args, **kwargs)
    sso = configuration.clean_sso_application_name(getattr(backend, 'sso'))
    extra_data_key = '_'.join(['extra_data', sso])

    data = {
        'expires_on': extra_data.get('expires_on'),
        'access_token': extra_data.get('access_token'),
        'expires': extra_data.get('expires'),
        'auth_time': extra_data.get('auth_time'),
        'refresh_token': extra_data.get('refresh_token'),
        'token_updated': int(time.time())
    }

    extra_data_str = json.dumps(data)

    if settings.COOKIE_COMPRESS:
        extra_data_str = compress_data(extra_data_str)

    strategy.session_set(extra_data_key, extra_data_str, secure=not settings.COOKIE_COMPRESS)

    return {
        'extra_data': extra_data
    }


def return_result(details, extra_data, *args, **kwargs):
    user = User()
    user.details = details
    user.extra_data = extra_data

    return {
        'user': user
    }
