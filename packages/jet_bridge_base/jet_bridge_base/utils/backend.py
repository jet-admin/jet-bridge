import requests

from jet_bridge_base import settings
from jet_bridge_base.configuration import configuration
from jet_bridge_base.logger import logger


def api_method_url(method):
    return '{}/{}'.format(settings.API_BASE_URL, method)


def is_token_activated(project_token):
    if not project_token:
        return False

    url = api_method_url('project_tokens/{}/'.format(project_token))
    headers = {
        'User-Agent': '{} v{}'.format(configuration.get_type(), configuration.get_version())
    }

    r = requests.request('GET', url, headers=headers)
    success = 200 <= r.status_code < 300

    if not success:
        return False

    result = r.json()

    return bool(result.get('activated'))


def project_auth(token, project_token, permission=None, params=None):
    if not project_token:
        return {
            'result': False
        }

    url = api_method_url('project_auth/')
    data = {
        'project_token': project_token,
        'token': token
    }
    headers = {
        'User-Agent': '{} v{}'.format(configuration.get_type(), configuration.get_version())
    }

    if permission:
        data.update(permission)

    if params:
        if 'project_child' in params:
            data['project_child'] = params['project_child']

    r = requests.request('POST', url, data=data, headers=headers)
    success = 200 <= r.status_code < 300

    if not success:
        logger.error('Project Auth request error: %d %s %s', r.status_code, r.reason, r.text)
        return {
            'result': False
        }

    result = r.json()

    if result.get('access_disabled'):
        return {
            'result': False,
            'warning': result.get('warning')
        }

    return {
        'result': True,
        'warning': result.get('warning')
    }


def get_resource_secret_tokens(project, resource, token):
    if not token:
        return []

    url = api_method_url('projects/{}/resources/{}/secret_tokens/'.format(project, resource))
    headers = {
        'Authorization': 'ProjectToken {}'.format(token),
        'User-Agent': '{} v{}'.format(configuration.get_type(), configuration.get_version())
    }

    r = requests.request('GET', url, headers=headers)
    success = 200 <= r.status_code < 300

    if not success:
        return []

    return r.json()


def get_secret_tokens(project, resource, token, user_token):
    if not token:
        return []

    url = api_method_url('projects/{}/secret_tokens/'.format(project))
    headers = {
        'Authorization': 'ProjectToken {}'.format(token),
        'User-Agent': '{} v{}'.format(configuration.get_type(), configuration.get_version())
    }
    data = {
        'resource': resource,
        'user_token': user_token
    }

    r = requests.request('POST', url, headers=headers, data=data)
    success = 200 <= r.status_code < 300

    if not success:
        return []

    return r.json()
