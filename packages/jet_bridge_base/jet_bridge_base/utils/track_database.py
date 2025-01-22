from datetime import datetime
from fnmatch import fnmatch
import requests

from jet_bridge_base import settings
from jet_bridge_base.configuration import configuration
from jet_bridge_base.db import get_request_connection
from jet_bridge_base.sentry import sentry_controller
from jet_bridge_base.utils.conf import get_conf

TRACK_DATABASES_THROTTLE = 60 * 15


def track_database(conf, connection):
    if not settings.TRACK_DATABASES_ENDPOINT:
        return

    current_track_date = datetime.now()
    latest_track_date = connection.get('tracked')

    if latest_track_date and (current_track_date - latest_track_date).total_seconds() < TRACK_DATABASES_THROTTLE:
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

        if success:
            connection['tracked'] = current_track_date
        else:
            error = 'TRACK_DATABASE request error: {} {} {}'.format(r.status_code, r.reason, r.text)
            sentry_controller.capture_message(error)
    except Exception as e:
        sentry_controller.capture_exception(e)


def track_database_async(request):
    if not settings.TRACK_DATABASES_ENDPOINT:
        return

    conf = get_conf(request)
    connection = get_request_connection(request)
    configuration.run_async(track_database, conf, connection)
