import json
import os
import re

from jet_bridge_base import settings
from jet_bridge_base.utils.common import merge
from jet_bridge_base.utils.crypt import get_sha256_hash
from jet_bridge_base.utils.text import clean_alphanumeric


def get_settings_conf():
    return {
        'engine': settings.DATABASE_ENGINE,
        'url': settings.DATABASE_URL,
        'host': settings.DATABASE_HOST,
        'port': settings.DATABASE_PORT,
        'name': settings.DATABASE_NAME,
        'user': settings.DATABASE_USER,
        'password': settings.DATABASE_PASSWORD,
        'extra': settings.DATABASE_EXTRA,
        'connections': settings.DATABASE_CONNECTIONS,
        'connections_overflow': settings.DATABASE_CONNECTIONS_OVERFLOW,
        'only': settings.DATABASE_ONLY,
        'except': settings.DATABASE_EXCEPT,
        'schema': settings.DATABASE_SCHEMA,
        'timezone': settings.DATABASE_TIMEZONE,
        'ssl_ca': settings.DATABASE_SSL_CA,
        'ssl_cert': settings.DATABASE_SSL_CERT,
        'ssl_key': settings.DATABASE_SSL_KEY,
        'ssh_host': settings.DATABASE_SSH_HOST,
        'ssh_port': settings.DATABASE_SSH_PORT,
        'ssh_user': settings.DATABASE_SSH_USER,
        'ssh_private_key': settings.DATABASE_SSH_PRIVATE_KEY,
        'project': settings.PROJECT,
        'token': settings.TOKEN
    }


def get_request_conf(request):
    bridge_settings = request.get_bridge_settings()

    if not bridge_settings:
        return

    return {
        'engine': bridge_settings.get('database_engine'),
        'url': bridge_settings.get('database_url'),
        'host': bridge_settings.get('database_host'),
        'port': bridge_settings.get('database_port'),
        'name': bridge_settings.get('database_name'),
        'user': bridge_settings.get('database_user'),
        'password': bridge_settings.get('database_password'),
        'extra': bridge_settings.get('database_extra'),
        'connections': bridge_settings.get('database_connections', settings.DATABASE_CONNECTIONS),
        'connections_overflow': bridge_settings.get('database_connections_overflow', settings.DATABASE_CONNECTIONS_OVERFLOW),
        'only': bridge_settings.get('database_only'),
        'except': bridge_settings.get('database_except'),
        'schema': bridge_settings.get('database_schema'),
        'timezone': bridge_settings.get('database_timezone'),
        'ssl_ca': bridge_settings.get('database_ssl_ca'),
        'ssl_cert': bridge_settings.get('database_ssl_cert'),
        'ssl_key': bridge_settings.get('database_ssl_key'),
        'ssh_host': bridge_settings.get('database_ssh_host'),
        'ssh_port': bridge_settings.get('database_ssh_port'),
        'ssh_user': bridge_settings.get('database_ssh_user'),
        'ssh_private_key': bridge_settings.get('database_ssh_private_key'),
        'project': bridge_settings.get('project'),
        'token': bridge_settings.get('token'),
    }


def get_conf(request):
    request_conf = get_request_conf(request)

    if request_conf:
        return request_conf
    else:
        return get_settings_conf()


def get_connection_id(conf):
    return get_sha256_hash(json.dumps([
        conf.get('engine'),
        conf.get('url'),
        conf.get('host'),
        conf.get('port'),
        conf.get('name'),
        conf.get('user'),
        conf.get('password'),
        conf.get('schema'),
        conf.get('timezone'),
        conf.get('ssl_ca'),
        conf.get('ssl_cert'),
        conf.get('ssl_key'),
        conf.get('ssh_host'),
        conf.get('ssh_port'),
        conf.get('ssh_user'),
        conf.get('ssh_private_key')
    ]))


def get_connection_meta_params_id(conf):
    return get_sha256_hash(json.dumps([
        conf.get('only'),
        conf.get('except'),
        conf.get('extra')
    ]))


def get_connection_params_id(conf):
    return json.dumps([
        conf.get('only'),
        conf.get('except'),
        conf.get('extra'),
        conf.get('connections'),
        conf.get('connections_overflow')
    ])


def is_tunnel_connection(conf):
    return all(map(lambda x: conf.get(x), ['ssh_host', 'ssh_port', 'ssh_user', 'ssh_private_key']))


def get_connection_schema(conf):
    schema = conf.get('schema') if conf.get('schema') and conf.get('schema') != '' else None

    if not schema and str(conf.get('engine', '')).startswith('mssql'):
        schema = 'dbo'

    return schema


def clean_connection_url(url):
    if not isinstance(url, str):
        return url
    return re.sub(r'//([^:]+):[^@/]+@', r'//\1:********@', url)


def get_connection_name(conf, schema):
    if conf.get('engine') == 'mongo':
        url = str(conf.get('url'))

        connection_name = [url]

        if not url.endswith('/'):
            connection_name.append('/')

        connection_name.append(conf.get('name') or '')

        return ''.join(connection_name)
    else:
        from jet_bridge_base.db_types.sql import sql_build_engine_url

        password_token = '__JET_DB_PASS__'
        log_conf = merge(merge({}, conf), {'password': password_token})

        connection_name = sql_build_engine_url(log_conf)
        if connection_name:
            connection_name = connection_name.replace(password_token, '********')
        if schema:
            connection_name += ':{}'.format(schema)
        if is_tunnel_connection(conf):
            connection_name += ' (via {}@{}:{})'.format(conf.get('ssh_user'), conf.get('ssh_host'), conf.get('ssh_port'))

        return connection_name


def get_connection_short_name_parts(conf):
    result = []

    if conf.get('url'):
        result.append(clean_connection_url(str(conf.get('url'))))
    else:
        if conf.get('engine'):
            result.append(str(conf.get('engine')))

        if conf.get('host'):
            result.append(str(conf.get('host')))

        if conf.get('port'):
            result.append(str(conf.get('port')))

    if conf.get('name'):
        result.append(str(conf.get('name')))

    return result


def get_connection_only_predicate(conf):
    def only(table):
        if conf.get('only') is not None and table not in conf.get('only'):
            return False
        if conf.get('except') is not None and table in conf.get('except'):
            return False
        return True
    return only


def get_metadata_file_path(conf):
    short_name = '_'.join(map(lambda x: clean_alphanumeric(x), get_connection_short_name_parts(conf)))
    id_hash = get_connection_id(conf)
    params_id_hash = get_connection_meta_params_id(conf)[:8]
    engine_length = len(str(conf.get('engine'))) + 1 if conf.get('engine') else 0
    file_name = '{}_{}_{}.dump'.format(short_name[:(50 + engine_length)], id_hash, params_id_hash)

    return os.path.join(settings.CACHE_METADATA_PATH, file_name)
