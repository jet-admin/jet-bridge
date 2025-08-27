import json

import requests

from jet_bridge_base import settings
from jet_bridge_base.configuration import configuration
from jet_bridge_base.encoders import JSONEncoder
from jet_bridge_base.sentry import sentry_controller


def track_model(project, environment, resource_token, model, action, uid, model_data, fields=None, invoker=None):
    if not settings.TRACK_MODELS_ENDPOINT:
        return

    if project is None or environment is None or resource_token is None:
        error = 'MODEL_CHANGE incorrect request: {} {} {}'.format(project, environment, resource_token)
        sentry_controller.capture_message(error)
        return

    url = '{}/model_change'.format(settings.TRACK_MODELS_ENDPOINT)
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        'project': project,
        'environment': environment,
        'resource_token': resource_token,
        'model': model,
        'action': action,
        'data': model_data
    }

    if uid is not None:
        data['id'] = uid

    if fields is not None:
        data['fields'] = fields

    if invoker is not None:
        data['invoker'] = invoker

    if settings.TRACK_MODELS_AUTH:
        headers['Authorization'] = settings.TRACK_MODELS_AUTH

    data_str = json.dumps(data, cls=JSONEncoder)

    try:
        r = requests.post(url, data=data_str, headers=headers)
        success = 200 <= r.status_code < 300

        if not success:
            error = 'MODEL_CHANGE request error: {} {} {}'.format(r.status_code, r.reason, r.text)
            sentry_controller.capture_message(error)
    except Exception as e:
        sentry_controller.capture_exception(e)


def track_model_async(request, model, action, uid, data, fields=None, invoker=None):
    if not settings.TRACK_MODELS_ENDPOINT:
        return

    configuration.run_async(track_model, request.project, request.environment, request.resource_token, model, action, uid, data, fields, invoker)
