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


settings_engine_url = None
connections = {}


def build_engine_url(
        DATABASE_ENGINE,
        DATABASE_HOST,
        DATABASE_PORT,
        DATABASE_NAME,
        DATABASE_USER,
        DATABASE_PASSWORD,
        DATABASE_EXTRA=''
):
    if not DATABASE_ENGINE or not DATABASE_NAME:
        return

    url = [
        str(DATABASE_ENGINE),
        '://'
    ]

    if DATABASE_ENGINE != 'sqlite':
        if DATABASE_USER:
            url.append(str(DATABASE_USER))

            if DATABASE_PASSWORD:
                url.append(':')
                url.append(str(DATABASE_PASSWORD))

            if DATABASE_HOST:
                url.append('@')

        if DATABASE_HOST:
            url.append(str(DATABASE_HOST))

            if DATABASE_PORT:
                url.append(':')
                url.append(str(DATABASE_PORT))

            url.append('/')

    if DATABASE_ENGINE == 'sqlite':
        url.append('/')

    url.append(str(DATABASE_NAME))

    if DATABASE_EXTRA:
        url.append(str(DATABASE_EXTRA))
    elif DATABASE_ENGINE == 'mysql':
        url.append('?charset=utf8')
    elif DATABASE_ENGINE == 'mssql+pyodbc':
        url.append('?driver=SQL+Server+Native+Client+11.0')

    return ''.join(url)


def build_engine_url_from_settings():
    return build_engine_url(
        settings.DATABASE_ENGINE,
        settings.DATABASE_HOST,
        settings.DATABASE_PORT,
        settings.DATABASE_NAME,
        settings.DATABASE_USER,
        settings.DATABASE_PASSWORD,
        settings.DATABASE_EXTRA
    )


def connect_database(engine_url, database_engine, schema):
    if database_engine == 'sqlite':
        engine = create_engine(engine_url)
    else:
        engine = create_engine(engine_url, pool_size=settings.DATABASE_CONNECTIONS, max_overflow=10, pool_recycle=1)

    Session = scoped_session(sessionmaker(bind=engine))

    logger.info('Connected to database engine "{}"'.format(engine_url))

    Base.metadata.create_all(engine)

    def only(table, meta):
        if settings.DATABASE_ONLY is not None and table not in settings.DATABASE_ONLY:
            return False
        if settings.DATABASE_EXCEPT is not None and table in settings.DATABASE_EXCEPT:
            return False
        return True

    metadata = MetaData(schema=schema if schema and schema != '' else None)
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

    connections[engine_url] = {
        'engine': engine,
        'Session': Session,
        'MappedBase': MappedBase
    }


def connect_database_from_settings():
    global settings_engine_url

    if settings.DATABASE_ENGINE == 'none':
        return

    settings_engine_url = build_engine_url_from_settings()

    if not settings_engine_url:
        raise Exception('Database configuration is not set')

    connect_database(settings_engine_url, settings.DATABASE_ENGINE, settings.DATABASE_SCHEMA)


def get_connection(request):
    global settings_engine_url

    bridge_settings_encoded = request.headers.get('X_BRIDGE_SETTINGS')

    if bridge_settings_encoded:
        from jet_bridge_base.utils.crypt import decrypt

        try:
            secret_key = settings.TOKEN.replace('-', '').lower()
            bridge_settings = json.loads(decrypt(bridge_settings_encoded, secret_key))
        except Exception:
            bridge_settings = {}

        engine_url = build_engine_url(
            bridge_settings.get('database_engine'),
            bridge_settings.get('database_host'),
            bridge_settings.get('database_port'),
            bridge_settings.get('database_name'),
            bridge_settings.get('database_user'),
            bridge_settings.get('database_password'),
            bridge_settings.get('database_extra')
        )
        database_engine = bridge_settings.get('database_engine')
        database_schema = bridge_settings.get('database_schema')
    else:
        engine_url = settings_engine_url
        database_engine = settings.DATABASE_ENGINE
        database_schema = settings.DATABASE_SCHEMA

    if engine_url and engine_url not in connections:
        connect_database(engine_url, database_engine, database_schema)

    return connections.get(engine_url)


def create_session(request):
    connection = get_connection(request)
    if not connection:
        return
    return connection['Session']()


def get_mapped_base(request):
    connection = get_connection(request)
    if not connection:
        return
    return connection['MappedBase']


def get_engine(request):
    connection = get_connection(request)
    if not connection:
        return
    return connection['engine']
