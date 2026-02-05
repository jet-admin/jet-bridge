import contextlib
import threading
from datetime import timedelta, datetime

from jet_bridge_base import settings
from jet_bridge_base.db_types import dump_metadata_file, load_mapped_base, init_database_connection, \
    fetch_default_timezone
from jet_bridge_base.logger import logger
from jet_bridge_base.ssh_tunnel import SSHTunnel
from jet_bridge_base.utils.common import get_random_string, format_size
from jet_bridge_base.utils.conf import get_connection_id, get_connection_schema, get_connection_name, \
    get_connection_params_id, is_tunnel_connection, get_conf, get_settings_conf
from jet_bridge_base.utils.datetime import date_trunc_minutes

connections = {}
pending_connections = {}
MODEL_DESCRIPTIONS_RESPONSE_CACHE_KEY = 'model_descriptions_response'
MODEL_DESCRIPTIONS_HASH_CACHE_KEY = 'model_descriptions_hash'


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

    hostname = conf.get('host')
    if is_hostname_blacklisted(hostname):
        raise Exception('Hostname "{}" is blacklisted'.format(hostname))

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

        database_connection = init_database_connection(
            conf,
            tunnel,
            id_short,
            connection_name,
            schema,
            pending_connection
        )

        connections[connection_id] = {
            'id': connection_id,
            'name': connection_name,
            'params_id': connection_params_id,
            'tunnel': tunnel,
            'cache': {},
            'lock': threading.Lock(),
            'project': conf.get('project'),
            'token': conf.get('token'),
            'init_start': init_start.isoformat(),
            'last_request': datetime.now(),
            **database_connection
        }

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

    default_timezone = connection.get('default_timezone')
    default_timezone_updated = connection.get('default_timezone_updated')

    if not default_timezone:
        return

    hour_now = date_trunc_minutes(datetime.now())
    hour_timezone_updated = date_trunc_minutes(default_timezone_updated)

    if hour_now.timestamp() != hour_timezone_updated.timestamp():
        conf = get_conf(request)
        connection_id = get_connection_id(conf)
        id_short = connection_id[:4]

        new_default_timezone = fetch_default_timezone(conf, request.session)
        new_default_timezone_updated = datetime.now()

        if new_default_timezone is not None:
            connection['default_timezone'] = new_default_timezone
            connection['default_timezone_updated'] = new_default_timezone_updated

            logger.info('[{}] Default timezone updated: "{}"'.format(id_short, default_timezone))

            return new_default_timezone
        else:
            logger.info('[{}] Failed to update default timezone'.format(id_short))

    return default_timezone


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
            cache['graphql_schema_base62'] = None
            cache['graphql_schema_base62_draft'] = None
        elif draft:
            cache['graphql_schema_draft'] = None
            cache['graphql_schema_base62_draft'] = None
        elif not draft:
            cache['graphql_schema'] = None
            cache['graphql_schema_base62'] = None


def reload_request_graphql_schema(request, draft=None):
    with request_connection_cache(request) as cache:
        if draft is None:
            cache['graphql_schema'] = None
            cache['graphql_schema_draft'] = None
            cache['graphql_schema_base62'] = None
            cache['graphql_schema_base62_draft'] = None
        elif draft:
            cache['graphql_schema_draft'] = None
            cache['graphql_schema_base62_draft'] = None
        elif not draft:
            cache['graphql_schema'] = None
            cache['graphql_schema_base62'] = None


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
        graphql_schema_base62 = cache.get('graphql_schema_base62')
        graphql_schema_base62_draft = cache.get('graphql_schema_base62_draft')

        if not graphql_schema and not graphql_schema_draft and not graphql_schema_base62 and not graphql_schema_base62_draft:
            continue

        time_elapsed = (datetime.now() - connection['last_request']).total_seconds()

        if time_elapsed <= settings.RELEASE_INACTIVE_GRAPHQL_SCHEMAS_TIMEOUT:
            continue

        graphql_schema_memory = graphql_schema.get('memory_usage_approx') if graphql_schema else 0
        graphql_schema_draft_memory = graphql_schema_draft.get('memory_usage_approx') if graphql_schema_draft else 0
        graphql_schema_base62_memory = graphql_schema_base62.get('memory_usage_approx') if graphql_schema_base62 else 0
        graphql_schema_base62_draft_memory = graphql_schema_base62_draft.get('memory_usage_approx') if graphql_schema_base62_draft else 0
        memory_usage_approx = graphql_schema_memory + graphql_schema_draft_memory + graphql_schema_base62_memory + graphql_schema_base62_draft_memory

        logger.info('Release inactive GraphQL schema "{}" (MEM:{}, ELAPSED:{})...'.format(
            connection['name'],
            format_size(memory_usage_approx) if memory_usage_approx else None,
            '{}s'.format(round(time_elapsed))
        ))

        reload_connection_graphql_schema(connection)
