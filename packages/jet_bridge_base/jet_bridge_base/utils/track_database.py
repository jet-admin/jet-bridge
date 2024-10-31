from fnmatch import fnmatch
import requests

from jet_bridge_base import settings
from jet_bridge_base.configuration import configuration
from jet_bridge_base.sentry import sentry_controller
from jet_bridge_base.utils.conf import get_conf


def track_database(conf):
    if not settings.TRACK_DATABASES_ENDPOINT:
        return

    track_databases = list(filter(lambda x: x != '', map(lambda x: x.lower().strip(), settings.TRACK_DATABASES.split(','))))
    hostname = '{}:{}'.format(conf.get('host', ''), conf.get('port', '')).lower()

    if not any(map(lambda x: fnmatch(hostname, x), track_databases)):
        return

    headers = {}
    data = {
        'databaseName': conf.get('name', ''),
        'databaseSchema': conf.get('schema', ''),
        'databaseHost': conf.get('host', ''),
        'databasePort': conf.get('port', '')
    }

    if settings.TRACK_DATABASES_AUTH:
        headers['Authorization'] = settings.TRACK_DATABASES_AUTH

    try:
        r = requests.post(settings.TRACK_DATABASES_ENDPOINT, headers=headers, json=data)
        success = 200 <= r.status_code < 300

        if not success:
            error = 'TRACK_DATABASE request error: {} {} {}'.format(r.status_code, r.reason, r.text)
            sentry_controller.capture_message(error)
    except Exception as e:
        sentry_controller.capture_exception(e)


def track_database_async(request):
    if not settings.TRACK_DATABASES_ENDPOINT:
        return

    conf = get_conf(request)
    configuration.run_async(track_database, conf)
