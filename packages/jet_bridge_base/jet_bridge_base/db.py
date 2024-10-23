import base64
import contextlib
import json
import os
import pickle
import re
import threading
import time
from datetime import timedelta, datetime

from jet_bridge_base.automap import automap_base
from jet_bridge_base.reflect import reflect
from jet_bridge_base.ssh_tunnel import SSHTunnel
from jet_bridge_base.utils.crypt import get_sha256_hash
from jet_bridge_base.utils.process import get_memory_usage_human, get_memory_usage
from jet_bridge_base.utils.timezones import fetch_default_timezone
from jet_bridge_base.utils.type_codes import fetch_type_code_to_sql_type
from six import StringIO
from six.moves.urllib_parse import quote_plus

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, scoped_session

from jet_bridge_base.utils.common import get_random_string, merge, format_size

try:
    from geoalchemy2 import types
except ImportError:
    pass

from jet_bridge_base import settings
from jet_bridge_base.logger import logger

connections = {}
pending_connections = {}
MODEL_DESCRIPTIONS_RESPONSE_CACHE_KEY = 'model_descriptions_response'
MODEL_DESCRIPTIONS_HASH_CACHE_KEY = 'model_descriptions_hash'


def url_encode(value):
    return quote_plus(value)


def build_engine_url(conf, tunnel=None):
    if not conf.get('engine') or not conf.get('name'):
        return

    url = [
        str(conf.get('engine')),
        '://'
    ]

    if conf.get('engine') == 'sqlite':
        url.append('/')
        url.append(str(conf.get('name')))

        if conf.get('extra'):
            url.append('?')
            url.append(str(conf.get('extra')))
    elif conf.get('engine') == 'bigquery':
        url.append(str(conf.get('name')))

        try:
            base64.b64decode(conf.get('password'))
            url.append('?credentials_base64={}'.format(conf.get('password')))

            if conf.get('extra'):
                url.append('&')
                url.append(str(conf.get('extra')))
        except:
            pass
    elif conf.get('engine') == 'snowflake':
        url.append(url_encode(str(conf.get('user'))))

        if conf.get('password'):
            url.append(':')
            url.append(url_encode(str(conf.get('password'))))

        url.append('@')

        url.append(str(conf.get('host')))
        url.append('/')

        url.append(str(conf.get('name')))

        if conf.get('extra'):
            url.append('?')
            url.append(str(conf.get('extra')))
    else:
        host = '127.0.0.1' if tunnel else conf.get('host')
        port = tunnel.local_bind_port if tunnel else conf.get('port')

        if conf.get('user'):
            url.append(url_encode(str(conf.get('user'))))

            if conf.get('password'):
                url.append(':')
                url.append(url_encode(str(conf.get('password'))))

            if host:
                url.append('@')

        if host:
            url.append(str(host))

            if port:
                url.append(':')
                url.append(str(port))

            url.append('/')

        if conf.get('engine') != 'oracle':
            url.append(str(conf.get('name')))

        if conf.get('extra'):
            url.append('?')
            url.append(str(conf.get('extra')))
        elif conf.get('engine') == 'mysql':
            url.append('?charset=utf8')
        elif conf.get('engine') == 'mssql+pyodbc':
            url.append('?driver=FreeTDS')
        elif conf.get('engine') == 'oracle':
            url.append('?service_name={}'.format(url_encode(conf.get('name'))))

    return ''.join(url)


def get_connection_id(conf):
    return get_sha256_hash(json.dumps([
        conf.get('engine'),
        conf.get('host'),
        conf.get('port'),
        conf.get('name'),
        conf.get('user'),
        conf.get('password'),
        conf.get('schema'),
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


def get_connection_tunnel(conf):
    if not is_tunnel_connection(conf):
        return

    schema = get_connection_schema(conf)
    connection_name = get_connection_name(conf, schema)

    # from sshtunnel import SSHTunnelForwarder, address_to_str
    # import paramiko
    #
    # class SafeSSHTunnelForwarder(SSHTunnelForwarder):
    #     skip_tunnel_checkup = False
    #
    #     def check_is_running(self):
    #         try:
    #             while True:
    #                 time.sleep(5)
    #                 if not tunnel.local_is_up(tunnel.local_bind_address):
    #                     logger.info('SSH tunnel is down, disposing connection "{}"'.format(connection_name))
    #                     break
    #         finally:
    #             dispose_connection(conf)
    #
    #     def start(self):
    #         super(SafeSSHTunnelForwarder, self).start()
    #
    #         for _srv in self._server_list:
    #             thread = threading.Thread(
    #                 target=self.check_is_running,
    #                 args=(),
    #                 name='Srv-{0}-check'.format(address_to_str(_srv.local_port))
    #             )
    #             thread.start()
    #
    # private_key_str = conf.get('ssh_private_key').replace('\\n', '\n')
    # private_key = paramiko.RSAKey.from_private_key(StringIO(private_key_str))
    #
    # tunnel = SafeSSHTunnelForwarder(
    #     ssh_address_or_host=(conf.get('ssh_host'), int(conf.get('ssh_port'))),
    #     ssh_username=conf.get('ssh_user'),
    #     ssh_pkey=private_key,
    #     remote_bind_address=(conf.get('host'), int(conf.get('port'))),
    #     logger=logger
    # )
    # tunnel.start()
    #
    # return tunnel

    logger.info('Starting SSH tunnel for connection "{}"...'.format(connection_name))

    def on_close():
        connection_id = get_connection_id(conf)
        connection = connections.get(connection_id)

        if connection:
            logger.info('SSH tunnel is closed, disposing connection "{}"'.format(connection_name))
            dispose_connection(conf)
        else:
            logger.info('SSH tunnel is closed for connection "{}"'.format(connection_name))

    tunnel = SSHTunnel(
        name=connection_name,
        ssh_host=conf.get('ssh_host'),
        ssh_port=conf.get('ssh_port'),
        ssh_user=conf.get('ssh_user'),
        ssh_private_key=conf.get('ssh_private_key').replace('\\n', '\n'),
        remote_host=conf.get('host'),
        remote_port=conf.get('port'),
        on_close=on_close
    )
    tunnel.start()

    logger.info('SSH tunnel started on port {} for connection "{}"'.format(tunnel.local_bind_port, connection_name))

    return tunnel


def get_connection_schema(conf):
    schema = conf.get('schema') if conf.get('schema') and conf.get('schema') != '' else None

    if not schema and conf.get('engine', '').startswith('mssql'):
        schema = 'dbo'

    return schema


def get_connection_name(conf, schema):
    password_token = '__JET_DB_PASS__'
    log_conf = merge(merge({}, conf), {'password': password_token})

    connection_name = build_engine_url(log_conf)
    if connection_name:
        connection_name = connection_name.replace(password_token, '********')
    if schema:
        connection_name += ':{}'.format(schema)
    if is_tunnel_connection(conf):
        connection_name += ' (via {}@{}:{})'.format(conf.get('ssh_user'), conf.get('ssh_host'), conf.get('ssh_port'))

    return connection_name


def get_connection_short_name_parts(conf):
    result = []

    if conf.get('engine'):
        result.append(str(conf.get('engine')))

    if conf.get('host'):
        result.append(str(conf.get('host')))

    if conf.get('port'):
        result.append(str(conf.get('port')))

    if conf.get('name'):
        result.append(str(conf.get('name')))

    return result


def wait_pending_connection(connection_id, connection_name):
    pending_connection = pending_connections.get(connection_id)
    if not pending_connection:
        return

    logger.info('Waiting database connection "{}"...'.format(connection_name))

    connected_condition = pending_connection['connected']
    with connected_condition:
        timeout = timedelta(minutes=10).total_seconds()
        connected_condition.wait(timeout=timeout)

    connection = connections.get(connection_id)
    if connection:
        logger.info('Found database connection "{}"'.format(connection_name))
        return connection
    else:
        logger.info('Not found database connection "{}"'.format(connection_name))


def create_connection_engine(conf, tunnel):
    engine_url = build_engine_url(conf, tunnel)

    if not engine_url:
        raise Exception('Database configuration is not set')

    if conf.get('engine') == 'sqlite':
        return create_engine(engine_url)
    elif conf.get('engine') == 'mysql':
        connect_args = {}
        ssl = {
            'ca': conf.get('ssl_ca'),
            'cert': conf.get('ssl_cert'),
            'key': conf.get('ssl_key')
        }
        ssl_set = dict(list(filter(lambda x: x[1], ssl.items())))

        if len(ssl_set):
            connect_args['ssl'] = ssl_set

        return create_engine(
            engine_url,
            pool_size=conf.get('connections'),
            pool_pre_ping=True,
            max_overflow=conf.get('connections_overflow'),
            pool_recycle=300,
            connect_args={
                'connect_timeout': 5,
                **connect_args
            }
        )
    elif conf.get('engine') == 'bigquery':
        return create_engine(
            engine_url,
            pool_size=conf.get('connections'),
            pool_pre_ping=True,
            max_overflow=conf.get('connections_overflow'),
            pool_recycle=300
        )
    elif conf.get('engine') == 'oracle':
        return create_engine(
            engine_url,
            pool_size=conf.get('connections'),
            pool_pre_ping=True,
            max_overflow=conf.get('connections_overflow'),
            pool_recycle=300
        )
    else:
        return create_engine(
            engine_url,
            pool_size=conf.get('connections'),
            pool_pre_ping=True,
            max_overflow=conf.get('connections_overflow'),
            pool_recycle=300,
            connect_args={'connect_timeout': 5}
        )


def get_connection_only_predicate(conf):
    def only(table, meta):
        if conf.get('only') is not None and table not in conf.get('only'):
            return False
        if conf.get('except') is not None and table in conf.get('except'):
            return False
        return True
    return only


def clean_hostname(hostname):
    if not isinstance(hostname, str):
        return
    hostname = hostname.strip().lower()
    if hostname == '':
        return
    return hostname


def get_blacklist_hostnames():
    hostnames = []

    if settings.BLACKLIST_HOSTS:
        hostnames.extend(settings.BLACKLIST_HOSTS.split(','))

    try:
        import configparser
    except ImportError:
        import ConfigParser as configparser

    try:
        config = configparser.RawConfigParser()
        config.read(settings.CONFIG)

        config_value = config.get('JET', 'BLACKLIST_HOSTS', fallback='')
        hostnames.extend(config_value.split(','))
    except:
        pass

    return list(filter(
        lambda x: x is not None,
        map(lambda x: clean_hostname(x), hostnames)
    ))


def is_hostname_blacklisted(hostname):
    hostname = clean_hostname(hostname)
    if not hostname:
        return False

    blacklist_hosts = get_blacklist_hostnames()
    if len(blacklist_hosts) == 0:
        return False

    return hostname in blacklist_hosts


def connect_database(conf):
    global connections, pending_connections

    connection_id = get_connection_id(conf)
    connection_params_id = get_connection_params_id(conf)
    schema = get_connection_schema(conf)
    connection_name = get_connection_name(conf, schema)
    id_short = connection_id[:4]

    existing_connection = connections.get(connection_id)
    if existing_connection:
        if existing_connection['params_id'] == connection_params_id:
            return existing_connection
        else:
            logger.info('[{}] Reconnecting to database "{}" because of different params ({} {})...'.format(
                id_short,
                connection_name,
                connection_params_id,
                existing_connection['params_id']
            ))
            dispose_connection(conf)

    init_start = datetime.now()

    connected_condition = threading.Condition()
    pending_connection_id = get_random_string(32)
    pending_connection = {
        'id': pending_connection_id,
        'name': connection_name,
        'project': conf.get('project'),
        'token': conf.get('token'),
        'init_start': init_start.isoformat(),
        'connected': connected_condition
    }

    existing_connection = wait_pending_connection(connection_id, connection_name)
    if existing_connection:
        return existing_connection

    pending_connections[connection_id] = pending_connection
    tunnel = None

    try:
        tunnel = get_connection_tunnel(conf)
        pending_connection['tunnel'] = tunnel

        engine = create_connection_engine(conf, tunnel)
        pending_connection['engine'] = engine

        hostname = conf.get('host')
        if is_hostname_blacklisted(hostname):
            raise Exception('Hostname "{}" is blacklisted'.format(hostname))

        Session = scoped_session(sessionmaker(bind=engine))
        session = Session()

        logger.info('[{}] Connecting to database "{}"...'.format(id_short, connection_name))

        connect_start = time.time()
        with session.connection() as connection:
            connect_end = time.time()
            connect_time = round(connect_end - connect_start, 3)

            logger.info('[{}] Getting db types for "{}"...'.format(id_short, connection_name))
            type_code_to_sql_type = fetch_type_code_to_sql_type(session)

            default_timezone = fetch_default_timezone(session)
            if default_timezone is not None:
                logger.info('[{}] Default timezone detected: "{}"'.format(id_short, default_timezone))
            else:
                logger.info('[{}] Failed to detect default timezone'.format(id_short))

            metadata_dump = load_metadata_file(conf, connection)

            if metadata_dump:
                metadata = metadata_dump['metadata']

                reflect_time = None
                reflect_memory_usage_approx = None

                logger.info('[{}] Loaded schema cache for "{}"'.format(id_short, connection_name))
            else:
                logger.info('[{}] Getting schema for "{}"...'.format(id_short, connection_name))

                reflect_start_time = time.time()
                reflect_start_memory_usage = get_memory_usage()

                metadata = MetaData(schema=schema, bind=connection)
                only = get_connection_only_predicate(conf)
                reflect(id_short, metadata, engine, only=only, pending_connection=pending_connection, foreign=True, views=True)

                reflect_end_time = time.time()
                reflect_end_memory_usage = get_memory_usage()
                reflect_time = round(reflect_end_time - reflect_start_time, 3)
                reflect_memory_usage_approx = reflect_end_memory_usage - reflect_start_memory_usage

                dump_metadata_file(conf, metadata)

            logger.info('[{}] Connected to "{}" (Mem:{})'.format(id_short, connection_name, get_memory_usage_human()))

            MappedBase = automap_base(metadata=metadata)
            load_mapped_base(MappedBase)

            for table_name, table in MappedBase.metadata.tables.items():
                if len(table.primary_key.columns) == 0 and table_name not in MappedBase.classes:
                    logger.warning('[{}] Table "{}" does not have primary key and will be ignored'.format(id_short, table_name))

            connections[connection_id] = {
                'id': connection_id,
                'name': connection_name,
                'engine': engine,
                'Session': Session,
                'MappedBase': MappedBase,
                'params_id': connection_params_id,
                'type_code_to_sql_type': type_code_to_sql_type,
                'default_timezone': default_timezone,
                'tunnel': tunnel,
                'cache': {},
                'lock': threading.Lock(),
                'project': conf.get('project'),
                'token': conf.get('token'),
                'init_start': init_start.isoformat(),
                'connect_time': connect_time,
                'reflect_time': reflect_time,
                'reflect_memory_usage_approx': reflect_memory_usage_approx,
                'reflect_metadata_dump': metadata_dump['file_path'] if metadata_dump else None,
                'last_request': datetime.now()
            }

        session.close()

        return connections[connection_id]
    except Exception as e:
        if tunnel:
            tunnel.close()

        raise e
    finally:
        if connection_id in pending_connections and pending_connections[connection_id].get('id') == pending_connection_id:
            del pending_connections[connection_id]

        with connected_condition:
            connected_condition.notify_all()


def clean_alphanumeric(str):
    return re.sub('[^0-9a-zA-Z.]+', '-', str)


def get_metadata_file_path(conf):
    short_name = '_'.join(map(lambda x: clean_alphanumeric(x), get_connection_short_name_parts(conf)))
    id_hash = get_connection_id(conf)
    params_id_hash = get_connection_meta_params_id(conf)[:8]
    engine_length = len(str(conf.get('engine'))) + 1 if conf.get('engine') else 0
    file_name = '{}_{}_{}.dump'.format(short_name[:(50 + engine_length)], id_hash, params_id_hash)

    return os.path.join(settings.CACHE_METADATA_PATH, file_name)


def dump_metadata_file(conf, metadata):
    if not settings.CACHE_METADATA:
        return

    connection_id = get_connection_id(conf)
    schema = get_connection_schema(conf)
    connection_name = get_connection_name(conf, schema)
    id_short = connection_id[:4]

    file_path = get_metadata_file_path(conf)

    try:
        dir_path = os.path.dirname(file_path)

        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)

        with open(file_path, 'wb') as file:
            pickle.dump(metadata, file)

        logger.info('[{}] Saved schema cache for "{}"'.format(id_short, connection_name))

        return file_path
    except Exception as e:
        logger.error('[{}] Failed dumping schema cache for "{}"'.format(id_short, connection_name), exc_info=e)


def load_metadata_file(conf, connection):
    if not settings.CACHE_METADATA:
        return

    connection_id = get_connection_id(conf)
    schema = get_connection_schema(conf)
    connection_name = get_connection_name(conf, schema)
    id_short = connection_id[:4]

    file_path = get_metadata_file_path(conf)

    if not os.path.exists(file_path):
        logger.info('[{}] Schema cache not found for "{}"'.format(id_short, connection_name))
        return

    try:
        with open(file_path, 'rb') as file:
            metadata = pickle.load(file=file)

        metadata.bind = connection

        return {
            'file_path': file_path,
            'metadata': metadata
        }
    except Exception as e:
        logger.error('[{}] Failed loading schema cache for "{}"'.format(id_short, connection_name), exc_info=e)


def remove_metadata_file(conf):
    if not settings.CACHE_METADATA:
        return

    connection_id = get_connection_id(conf)
    schema = get_connection_schema(conf)
    connection_name = get_connection_name(conf, schema)
    id_short = connection_id[:4]

    file_path = get_metadata_file_path(conf)

    if not os.path.exists(file_path):
        logger.info('[{}] Schema cache clear skipped (file not found) for "{}"'.format(id_short, connection_name))
        return

    try:
        os.unlink(file_path)
        logger.info('[{}] Schema cache cleared for "{}"'.format(id_short, connection_name))

        return file_path
    except Exception as e:
        logger.error('[{}] Schema cache clear failed for "{}"'.format(id_short, connection_name), exc_info=e)


def dispose_connection_object(connection):
    try:
        connection['engine'].dispose()

        if connection.get('tunnel'):
            connection['tunnel'].close()

        return True
    except Exception:
        return False


def dispose_connection(conf):
    global connections

    connection_id = get_connection_id(conf)
    connection = connections.get(connection_id)

    if connection and dispose_connection_object(connection):
        del connections[connection_id]
        return True

    return False


def dispose_request_connection(request):
    return dispose_connection(get_conf(request))


def get_settings_conf():
    return {
        'engine': settings.DATABASE_ENGINE,
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


def get_connection(request):
    conf = get_conf(request)
    connection_id = get_connection_id(conf)
    return connections.get(connection_id)


def connect_database_from_settings():
    if settings.DATABASE_ENGINE == 'none':
        return
    return connect_database(get_settings_conf())


def get_request_connection(request):
    return connect_database(get_conf(request))


def create_session(request):
    connection = get_request_connection(request)
    if not connection:
        return

    conf = get_conf(request)
    hostname = conf.get('host')
    if is_hostname_blacklisted(hostname):
        dispose_connection(conf)
        raise Exception('Hostname "{}" is blacklisted'.format(hostname))

    return connection['Session']()


def get_connection_id_short(request):
    connection = get_request_connection(request)
    if not connection or 'id' not in connection:
        return
    return connection['id'][:4]


def get_mapped_base(request):
    connection = get_request_connection(request)
    if not connection:
        return
    return connection['MappedBase']


def get_engine(request):
    connection = get_request_connection(request)
    if not connection:
        return
    return connection['engine']


def get_type_code_to_sql_type(request):
    connection = get_request_connection(request)
    if not connection:
        return
    return connection['type_code_to_sql_type']


def get_default_timezone(request):
    connection = get_request_connection(request)
    if not connection:
        return
    return connection['default_timezone']


@contextlib.contextmanager
def connection_cache(connection):
    if not connection:
        yield {}
    with connection['lock']:
        yield connection['cache']


@contextlib.contextmanager
def request_connection_cache(request):
    connection = get_request_connection(request)
    if not connection:
        yield {}
    with connection['lock']:
        yield connection['cache']


def connection_cache_get(request, name, default=None):
    connection = get_request_connection(request)
    if not connection:
        return
    with connection['lock']:
        return connection['cache'].get(name, default)


def connection_cache_set(request, name, value):
    connection = get_request_connection(request)
    if not connection:
        return
    with connection['lock']:
        connection['cache'][name] = value


def reload_request_mapped_base(request):
    conf = get_conf(request)
    MappedBase = get_mapped_base(request)

    load_mapped_base(MappedBase, True)
    reload_request_model_descriptions_cache(request)
    reload_request_graphql_schema(request)
    dump_metadata_file(conf, MappedBase.metadata)


def reload_connection_graphql_schema(connection, draft=None):
    with connection_cache(connection) as cache:
        if draft is None:
            cache['graphql_schema'] = None
            cache['graphql_schema_draft'] = None
        else:
            schema_key = 'graphql_schema_draft' if draft else 'graphql_schema'
            cache[schema_key] = None


def reload_request_graphql_schema(request, draft=None):
    with request_connection_cache(request) as cache:
        if draft is None:
            cache['graphql_schema'] = None
            cache['graphql_schema_draft'] = None
        else:
            schema_key = 'graphql_schema_draft' if draft else 'graphql_schema'
            cache[schema_key] = None


def reload_request_model_descriptions_cache(request):
    with request_connection_cache(request) as cache:
        cache[MODEL_DESCRIPTIONS_RESPONSE_CACHE_KEY] = None
        cache[MODEL_DESCRIPTIONS_HASH_CACHE_KEY] = None


def release_inactive_graphql_schemas():
    if not settings.RELEASE_INACTIVE_GRAPHQL_SCHEMAS_TIMEOUT:
        return

    for connection in connections.values():
        cache = connection['cache']
        graphql_schema = cache.get('graphql_schema')
        graphql_schema_draft = cache.get('graphql_schema_draft')

        if not graphql_schema and not graphql_schema_draft:
            continue

        time_elapsed = (datetime.now() - connection['last_request']).total_seconds()

        if time_elapsed <= settings.RELEASE_INACTIVE_GRAPHQL_SCHEMAS_TIMEOUT:
            continue

        graphql_schema_memory = graphql_schema.get('memory_usage_approx') if graphql_schema else 0
        graphql_schema_draft_memory = graphql_schema_draft.get('memory_usage_approx') if graphql_schema_draft else 0
        memory_usage_approx = graphql_schema_memory + graphql_schema_draft_memory

        logger.info('Release inactive GraphQL schema "{}" (MEM:{}, ELAPSED:{})...'.format(
            connection['name'],
            format_size(memory_usage_approx) if memory_usage_approx else None,
            '{}s'.format(round(time_elapsed))
        ))

        reload_connection_graphql_schema(connection)


def get_table_name(metadata, table):
    if table.schema and table.schema != metadata.schema:
        return '{}.{}'.format(table.schema, table.name)
    else:
        return str(table.name)


def load_mapped_base(MappedBase, clear=False):
    def classname_for_table(base, tablename, table):
        return get_table_name(MappedBase.metadata, table)

    def name_for_scalar_relationship(base, local_cls, referred_cls, constraint):
        foreign_key = constraint.elements[0] if len(constraint.elements) else None
        if foreign_key:
            name = '__'.join([foreign_key.parent.name, 'to', foreign_key.column.table.name, foreign_key.column.name])
        else:
            name = referred_cls.__name__.lower()

        if name in constraint.parent.columns:
            name = name + '_relation'
            logger.warning('Already detected column name, using {}'.format(name))

        return name

    def name_for_collection_relationship(base, local_cls, referred_cls, constraint):
        foreign_key = constraint.elements[0] if len(constraint.elements) else None
        if foreign_key:
            name = '__'.join([foreign_key.parent.table.name, foreign_key.parent.name, 'to', foreign_key.column.name])
        else:
            name = referred_cls.__name__.lower()

        if name in constraint.parent.columns:
            name = name + '_relation'
            logger.warning('Already detected column name, using {}'.format(name))

        return name

    if clear:
        MappedBase.registry.dispose()
        MappedBase.classes.clear()

    MappedBase.prepare(
        classname_for_table=classname_for_table,
        name_for_scalar_relationship=name_for_scalar_relationship,
        name_for_collection_relationship=name_for_collection_relationship
    )

