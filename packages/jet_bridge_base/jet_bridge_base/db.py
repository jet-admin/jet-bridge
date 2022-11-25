import base64
import contextlib
import json
import threading

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


def get_connection_tunnel(conf):
    if any(map(lambda x: not conf.get(x), ['ssh_host', 'ssh_port', 'ssh_user', 'ssh_private_key'])):
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


def connect_database(conf):
    global connections

    connection_id = get_connection_id(conf)
    connection_params_id = get_connection_params_id(conf)

    if connection_id in connections:
        if connections[connection_id]['params_id'] == connection_params_id:
            return connections[connection_id]
        else:
            disconnect_database(conf)

    tunnel = get_connection_tunnel(conf)
    engine_url = build_engine_url(conf, tunnel)

    if not engine_url:
        raise Exception('Database configuration is not set')

    def get_engine():
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


    engine = get_engine()

    Session = scoped_session(sessionmaker(bind=engine))

    def only(table, meta):
        if conf.get('only') is not None and table not in conf.get('only'):
            return False
        if conf.get('except') is not None and table in conf.get('except'):
            return False
        return True

    schema = conf.get('schema') if conf.get('schema') and conf.get('schema') != '' else None

    if not schema and conf.get('engine', '').startswith('mssql'):
        schema = 'dbo'


    session = Session()

    password_token = '__JET_DB_PASS__'
    log_conf = merge(merge({}, conf), {'password': password_token})
    log_address = build_engine_url(log_conf)
    if log_address:
        log_address = log_address.replace(password_token, '********')
    if tunnel:
        log_address += ' (via {}@{}:{})'.format(conf.get('ssh_user'), conf.get('ssh_host'), conf.get('ssh_port'))

    logger.info('Connecting to database "{}"...'.format(log_address))

    with session.connection() as connection:
        logger.info('Getting db types for "{}"...'.format(log_address))
        type_code_to_sql_type = fetch_type_code_to_sql_type(session)

        metadata = MetaData(schema=schema, bind=connection)
        logger.info('Getting schema for "{}"...'.format(log_address))
        reflect(metadata, engine, only=only)
        logger.info('Connected to "{}"...'.format(log_address))

        MappedBase = automap_base(metadata=metadata)
        load_mapped_base(MappedBase)

        for table_name, table in MappedBase.metadata.tables.items():
            if len(table.primary_key.columns) == 0 and table_name not in MappedBase.classes:
                logger.warning('Table "{}" does not have primary key and will be ignored'.format(table_name))

        connections[connection_id] = {
            'id': connection_id,
            'engine': engine,
            'Session': Session,
            'MappedBase': MappedBase,
            'params_id': connection_params_id,
            'type_code_to_sql_type': type_code_to_sql_type,
            'tunnel': tunnel,
            'cache': {},
            'lock': threading.Lock()
        }

    session.close()
    return connections[connection_id]


def disconnect_database(conf):
    global connections

    connection_id = get_connection_id(conf)

    if connection_id in connections:
        try:
            connections[connection_id]['engine'].dispose()

            if connections[connection_id]['tunnel']:
                connections[connection_id]['tunnel'].close()

            del connections[connection_id]
            return True
        except Exception:
            pass

    return False


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
        'ssh_private_key': settings.DATABASE_SSH_PRIVATE_KEY
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
        'ssh_private_key': bridge_settings.get('database_ssh_private_key')
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


def dispose_connection(request):
    return disconnect_database(get_conf(request))
