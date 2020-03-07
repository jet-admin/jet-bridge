import json

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.automap import automap_base, generate_relationship
from sqlalchemy.orm import sessionmaker, scoped_session

from jet_bridge_base.utils.common import get_random_string

try:
    from geoalchemy2 import types
except ImportError:
    pass

from jet_bridge_base import settings
from jet_bridge_base.models import Base
from jet_bridge_base.logger import logger


connections = {}


def build_engine_url(conf):
    if not conf.get('engine') or not conf.get('name'):
        return

    url = [
        str(conf.get('engine')),
        '://'
    ]

    if conf.get('engine') != 'sqlite':
        if conf.get('user'):
            url.append(str(conf.get('user')))

            if conf.get('password'):
                url.append(':')
                url.append(str(conf.get('password')))

            if conf.get('host'):
                url.append('@')

        if conf.get('host'):
            url.append(str(conf.get('host')))

            if conf.get('port'):
                url.append(':')
                url.append(str(conf.get('port')))

            url.append('/')

    if conf.get('engine') == 'sqlite':
        url.append('/')

    url.append(str(conf.get('name')))

    if conf.get('extra'):
        url.append(str(conf.get('extra')))
    elif conf.get('engine') == 'mysql':
        url.append('?charset=utf8')
    elif conf.get('engine') == 'mssql+pyodbc':
        url.append('?driver=FreeTDS')

    return ''.join(url)


def get_connection_id(conf):
    return json.dumps([
        conf.get('engine'),
        conf.get('host'),
        conf.get('port'),
        conf.get('name'),
        conf.get('user'),
        conf.get('password'),
        conf.get('only'),
        conf.get('except'),
        conf.get('schema')
    ])


def get_connection_params_id(conf):
    return json.dumps([
        conf.get('extra'),
        conf.get('connections')
    ])


def connect_database(conf):
    global connections

    engine_url = build_engine_url(conf)

    if not engine_url:
        raise Exception('Database configuration is not set')

    connection_id = get_connection_id(conf)
    connection_params_id = get_connection_params_id(conf)

    if connection_id in connections:
        if connections[connection_id]['params_id'] == connection_params_id:
            return connections[connection_id]
        else:
            disconnect_database(conf)

    if conf.get('engine') == 'sqlite':
        engine = create_engine(engine_url)
    else:
        engine = create_engine(engine_url, pool_size=conf.get('connections'), max_overflow=10, pool_recycle=1)

    Session = scoped_session(sessionmaker(bind=engine))

    logger.info('Connected to database engine "{}"'.format(engine_url))

    Base.metadata.create_all(engine)

    def only(table, meta):
        if conf.get('only') is not None and table not in conf.get('only'):
            return False
        if conf.get('except') is not None and table in conf.get('except'):
            return False
        return True

    metadata = MetaData(schema=conf.get('schema') if conf.get('schema') and conf.get('schema') != '' else None)
    metadata.reflect(engine, only=only)
    MappedBase = automap_base(metadata=metadata)

    def name_for_scalar_relationship(base, local_cls, referred_cls, constraint):
        rnd = get_random_string(4)
        return referred_cls.__name__.lower() + '_jet_relation' + rnd

    def name_for_collection_relationship(base, local_cls, referred_cls, constraint):
        rnd = get_random_string(4)
        return referred_cls.__name__.lower() + '_jet_collection' + rnd

    def custom_generate_relationship(base, direction, return_fn, attrname, local_cls, referred_cls, **kw):
        rnd = get_random_string(4)
        attrname = attrname + '_jet_ref' + rnd
        return generate_relationship(base, direction, return_fn, attrname, local_cls, referred_cls, **kw)

    MappedBase.prepare(
        name_for_scalar_relationship=name_for_scalar_relationship,
        name_for_collection_relationship=name_for_collection_relationship,
        generate_relationship=custom_generate_relationship
    )

    for table_name, table in MappedBase.metadata.tables.items():
        if len(table.primary_key.columns) == 0 and table_name not in MappedBase.classes:
            logger.warning('Table "{}" does not have primary key and will be ignored'.format(table_name))

    connections[connection_id] = {
        'engine': engine,
        'Session': Session,
        'MappedBase': MappedBase,
        'params_id': connection_params_id
    }
    return connections[connection_id]


def disconnect_database(conf):
    global connections

    connection_id = get_connection_id(conf)

    if connection_id in connections:
        try:
            connections[connection_id]['engine'].dispose()
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
        'schema': settings.DATABASE_SCHEMA
    }


def get_request_conf(bridge_settings_encoded):
    from jet_bridge_base.utils.crypt import decrypt

    try:
        secret_key = settings.TOKEN.replace('-', '').lower()
        bridge_settings = json.loads(decrypt(bridge_settings_encoded, secret_key))
    except Exception:
        bridge_settings = {}

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
    }


def get_conf(request):
    bridge_settings_encoded = request.headers.get('X_BRIDGE_SETTINGS')

    if bridge_settings_encoded:
        return get_request_conf(bridge_settings_encoded)
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


def dispose_connection(request):
    return disconnect_database(get_conf(request))
