import requests

from jet_bridge_base import settings
from jet_bridge_base.utils.async_exec import as_future


def track_model(request, model, action, uid, data):
    if not settings.TRACK_MODELS_ENDPOINT:
        return

    if request.project is None or request.environment is None or request.resource_token is None:
        return

    url = '{}/model_change'.format(settings.TRACK_MODELS_ENDPOINT)
    headers = {}
    data = {
        'project': request.project,
        'environment': request.environment,
        'resource_token': request.resource_token,
        'model': model,
        'action': action,
        'data': data
    }

    if uid is not None:
        data['id'] = uid

    if settings.TRACK_MODELS_AUTH:
        headers['Authorization'] = settings.TRACK_MODELS_AUTH

    requests.post(url, data, headers=headers)


def track_model_async(request, model, action, uid, data):
    if not settings.TRACK_MODELS_ENDPOINT:
        return

    try:
        import asyncio
    except:
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    as_future(lambda: track_model(request, model, action, uid, data))
