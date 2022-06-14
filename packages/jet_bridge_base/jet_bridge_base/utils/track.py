from fnmatch import fnmatch
import requests

from jet_bridge_base import settings
from jet_bridge_base.db import get_conf
from jet_bridge_base.utils.async_exec import as_future


def track_database(request):
    if not settings.TRACK_DATABASES_ENDPOINT:
        return

    track_databases = list(filter(lambda x: x != '', map(lambda x: x.lower().strip(), settings.TRACK_DATABASES.split(','))))
    conf = get_conf(request)
    hostname = '{}:{}'.format(conf.get('host', ''), conf.get('port', '')).lower()

    if any(map(lambda x: fnmatch(hostname, x), track_databases)):
        headers = {}
        data = {
            'databaseName': conf.get('name', ''),
            'databaseSchema': conf.get('schema', ''),
            'databaseHost': conf.get('host', ''),
            'databasePort': conf.get('port', '')
        }

        if settings.TRACK_DATABASES_AUTH:
            headers['Authorization'] = settings.TRACK_DATABASES_AUTH

        requests.request('POST', settings.TRACK_DATABASES_ENDPOINT, headers=headers, json=data)


def track_database_async(request):
    if not settings.TRACK_DATABASES_ENDPOINT:
        return

    try:
        import asyncio
    except:
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    as_future(lambda: track_database(request))
