import base64
import contextlib
import json
import threading
import time
from datetime import timedelta, datetime

from jet_bridge_base.reflect import reflect
from jet_bridge_base.utils.crypt import get_sha256_hash
from jet_bridge_base.utils.type_codes import fetch_type_code_to_sql_type
from six import StringIO
from six.moves.urllib_parse import quote_plus

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.automap import automap_base, generate_relationship
from sqlalchemy.orm import sessionmaker, scoped_session

from jet_bridge_base.utils.common import get_random_string, merge

try:
    from geoalchemy2 import types
except ImportError:
    pass

from jet_bridge_base import settings
from jet_bridge_base.logger import logger

connections = {}
pending_connections = {}


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

        url.append(str(conf.get('name')))

        if conf.get('extra'):
            url.append('?')
            url.append(str(conf.get('extra')))
        elif conf.get('engine') == 'mysql':
            url.append('?charset=utf8')
        elif conf.get('engine') == 'mssql+pyodbc':
            url.append('?driver=FreeTDS')

    return ''.join(url)


def get_connection_id(conf):
    return get_sha256_hash(json.dumps([
        conf.get('engine'),
        conf.get('host'),
        conf.get('port'),
        conf.get('name'),
        conf.get('user'),
        conf.get('password'),
        conf.get('only'),
        conf.get('except'),
        conf.get('schema'),
        conf.get('ssh_host'),
        conf.get('ssh_port'),
        conf.get('ssh_user'),
        conf.get('ssh_private_key')
    ]))


def get_connection_params_id(conf):
    return json.dumps([
        conf.get('extra'),
        conf.get('connections')
    ])


def is_tunnel_connection(conf):
    return all(map(lambda x: conf.get(x), ['ssh_host', 'ssh_port', 'ssh_user', 'ssh_private_key']))


def get_connection_tunnel(conf):
    if not is_tunnel_connection(conf):
        return

    from sshtunnel import SSHTunnelForwarder
    import paramiko

    private_key_str = conf.get('ssh_private_key').replace('\\n', '\n')
    private_key = paramiko.RSAKey.from_private_key(StringIO(private_key_str))

    server = SSHTunnelForwarder(
        ssh_address_or_host=(conf.get('ssh_host'), int(conf.get('ssh_port'))),
        ssh_username=conf.get('ssh_user'),
        ssh_pkey=private_key,
        remote_bind_address=(conf.get('host'), int(conf.get('port'))),
        logger=logger
    )
    server.start()

    return server


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


def wait_pending_connection(connection_id, connection_name):
    if connection_id not in pending_connections:
        return

    pending_connection = pending_connections[connection_id]

    logger.info('Waiting database connection "{}"...'.format(connection_name))

    connected_condition = pending_connection['connected']
    with connected_condition:
        timeout = timedelta(minutes=10).total_seconds()
        connected_condition.wait(timeout=timeout)

    if connection_id in connections:
        logger.info('Found database connection "{}"'.format(connection_name))
        return connections[connection_id]
    else:
        logger.info('Not found database connection "{}"'.format(connection_name))


def create_connection_engine(conf, tunnel):
    engine_url = build_engine_url(conf, tunnel)

    if not engine_url:
        raise Exception('Database configuration is not set')

    if conf.get('engine') == 'sqlite':
        return create_engine(engine_url)
    elif conf.get('engine') == 'bigquery':
        return create_engine(
            engine_url,
            pool_size=conf.get('connections'),
            pool_pre_ping=True,
            max_overflow=1,
            pool_recycle=300
        )
    else:
        return create_engine(
            engine_url,
            pool_size=conf.get('connections'),
            pool_pre_ping=True,
            max_overflow=1,
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


def connect_database(conf):
    global connections, pending_connections

    connection_id = get_connection_id(conf)
    connection_params_id = get_connection_params_id(conf)

    if connection_id in connections:
        if connections[connection_id]['params_id'] == connection_params_id:
            return connections[connection_id]
        else:
            dispose_connection(conf)

    schema = get_connection_schema(conf)
    connection_name = get_connection_name(conf, schema)

    existing_connection = wait_pending_connection(connection_id, connection_name)
    if existing_connection:
        return existing_connection

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

    pending_connections[connection_id] = pending_connection
    tunnel = None

    try:
        tunnel = get_connection_tunnel(conf)
        pending_connection['tunnel'] = tunnel

        engine = create_connection_engine(conf, tunnel)
        pending_connection['engine'] = engine

        Session = scoped_session(sessionmaker(bind=engine))
        session = Session()

        logger.info('Connecting to database "{}"...'.format(connection_name))

        connect_start = time.time()
        with session.connection() as connection:
            connect_end = time.time()
            connect_time = round(connect_end - connect_start, 3)

            logger.info('Getting db types for "{}"...'.format(connection_name))
            type_code_to_sql_type = fetch_type_code_to_sql_type(session)

            logger.info('Getting schema for "{}"...'.format(connection_name))

            reflect_start = time.time()

            metadata = MetaData(schema=schema, bind=connection)
            only = get_connection_only_predicate(conf)
            reflect(metadata, engine, only=only, pending_connection=pending_connection)

            reflect_end = time.time()
            reflect_time = round(reflect_end - reflect_start, 3)

            logger.info('Connected to "{}"'.format(connection_name))

            MappedBase = automap_base(metadata=metadata)
            load_mapped_base(MappedBase)

            for table_name, table in MappedBase.metadata.tables.items():
                if len(table.primary_key.columns) == 0 and table_name not in MappedBase.classes:
                    logger.warning('Table "{}" does not have primary key and will be ignored'.format(table_name))

            connections[connection_id] = {
                'id': connection_id,
                'name': connection_name,
                'engine': engine,
                'Session': Session,
                'MappedBase': MappedBase,
                'params_id': connection_params_id,
                'type_code_to_sql_type': type_code_to_sql_type,
                'tunnel': tunnel,
                'cache': {},
                'lock': threading.Lock(),
                'project': conf.get('project'),
                'token': conf.get('token'),
                'init_start': init_start.isoformat(),
                'connect_time': connect_time,
                'reflect_time': reflect_time
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
        'only': settings.DATABASE_ONLY,
        'except': settings.DATABASE_EXCEPT,
        'schema': settings.DATABASE_SCHEMA,
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
        'connections': bridge_settings.get('database_connections', 50),
        'only': bridge_settings.get('database_only'),
        'except': bridge_settings.get('database_except'),
        'schema': bridge_settings.get('database_schema'),
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
    return connection['Session']()


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


@contextlib.contextmanager
def connection_cache(request):
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
    MappedBase = get_mapped_base(request)
    load_mapped_base(MappedBase, True)
    reload_request_graphql_schema(request)


def reload_request_graphql_schema(request, draft=None):
    with connection_cache(request) as cache:
        if draft is None:
            cache['graphql_schema'] = None
            cache['graphql_schema_draft'] = None
        else:
            schema_key = 'graphql_schema_draft' if draft else 'graphql_schema'
            cache[schema_key] = None


def load_mapped_base(MappedBase, clear=False):
    def classname_for_table(base, tablename, table):
        if table.schema and table.schema != MappedBase.metadata.schema:
            return '{}.{}'.format(table.schema, tablename)
        else:
            return tablename

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

