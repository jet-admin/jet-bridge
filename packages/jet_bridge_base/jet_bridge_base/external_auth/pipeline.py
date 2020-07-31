import json

from jet_bridge_base.configuration import configuration
from jet_bridge_base.external_auth.storage import User


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
    }

    strategy.session_set(extra_data_key, json.dumps(data))

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
