import json
from six.moves.urllib_parse import quote_plus

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

def url_encode(value):
    return quote_plus(value)

def build_engine_url(conf):
    if not conf.get('engine') or not conf.get('name'):
        return

    url = [
        str(conf.get('engine')),
        '://'
    ]

    if conf.get('engine') != 'sqlite':
        if conf.get('user'):
            url.append(url_encode(str(conf.get('user'))))

            if conf.get('password'):
                url.append(':')
                url.append(url_encode(str(conf.get('password'))))

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
        engine = create_engine(engine_url, pool_size=conf.get('connections'), pool_pre_ping=True, max_overflow=1, pool_recycle=300, connect_args={'connect_timeout': 5})

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

    logger.info('Connecting to database "{}"...'.format(engine_url))

    with session.connection() as connection:
        metadata = MetaData(schema=schema, bind=connection)
        logger.info('Getting schema for "{}"...'.format(engine_url))
        metadata.reflect(engine, only=only)
        logger.info('Connected to "{}"...'.format(engine_url))

        MappedBase = automap_base(metadata=metadata)
        reload_mapped_base(MappedBase)

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


def reload_mapped_base(MappedBase):
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

    MappedBase.classes.clear()
    MappedBase.prepare(
        name_for_scalar_relationship=name_for_scalar_relationship,
        name_for_collection_relationship=name_for_collection_relationship,
        generate_relationship=custom_generate_relationship
    )


def dispose_connection(request):
    return disconnect_database(get_conf(request))
