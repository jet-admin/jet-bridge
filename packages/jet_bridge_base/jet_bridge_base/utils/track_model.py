import json

import requests

from jet_bridge_base import settings
from jet_bridge_base.encoders import JSONEncoder
from jet_bridge_base.sentry import sentry_controller
from jet_bridge_base.utils.async_exec import pool_submit


def track_model(request, model, action, uid, model_data):
    if not settings.TRACK_MODELS_ENDPOINT:
        return

    if request.project is None or request.environment is None or request.resource_token is None:
        error = 'MODEL_CHANGE incorrect request: {} {} {}'.format(request.project, request.environment, request.resource_token)
        sentry_controller.capture_message(error)
        return

    url = '{}/model_change'.format(settings.TRACK_MODELS_ENDPOINT)
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        'project': request.project,
        'environment': request.environment,
        'resource_token': request.resource_token,
        'model': model,
        'action': action,
        'data': model_data
    }

    if uid is not None:
        data['id'] = uid

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


def track_model_async(request, model, action, uid, data):
    if not settings.TRACK_MODELS_ENDPOINT:
        return

    pool_submit(track_model, request, model, action, uid, data)
