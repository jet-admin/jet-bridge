import base64
import time
from six.moves.urllib_parse import quote_plus
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from jet_bridge_base.automap import automap_base
from jet_bridge_base.utils.conf import get_connection_only_predicate
from jet_bridge_base.utils.process import get_memory_usage_human, get_memory_usage
from jet_bridge_base.utils.tables import get_table_name
from jet_bridge_base.logger import logger

from .sql_metadata_file import sql_load_metadata_file, sql_dump_metadata_file
from .sql_reflect import sql_reflect
from .timezones import sql_fetch_default_timezone
from .type_codes import fetch_type_code_to_sql_type


def sql_init_database_connection(conf, tunnel, id_short, connection_name, schema, pending_connection):
    engine = sql_create_connection_engine(conf, tunnel)
    pending_connection['engine'] = engine

    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()

    logger.info('[{}] Connecting to database "{}"...'.format(id_short, connection_name))

    connect_start = time.time()
    with session.connection() as connection:
        connect_end = time.time()
        connect_time = round(connect_end - connect_start, 3)

        logger.info('[{}] Getting db types for "{}"...'.format(id_short, connection_name))
        type_code_to_sql_type = fetch_type_code_to_sql_type(session)

        default_timezone = sql_fetch_default_timezone(session)
        if default_timezone is not None:
            logger.info('[{}] Default timezone detected: "{}"'.format(id_short, default_timezone))
        else:
            logger.info('[{}] Failed to detect default timezone'.format(id_short))

        metadata_dump = sql_load_metadata_file(conf, connection)

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
            sql_reflect(id_short, metadata, engine, only=only, pending_connection=pending_connection, foreign=True, views=True)

            reflect_end_time = time.time()
            reflect_end_memory_usage = get_memory_usage()
            reflect_time = round(reflect_end_time - reflect_start_time, 3)
            reflect_memory_usage_approx = reflect_end_memory_usage - reflect_start_memory_usage

            sql_dump_metadata_file(conf, metadata)

        logger.info('[{}] Connected to "{}" (Mem:{})'.format(id_short, connection_name, get_memory_usage_human()))

        MappedBase = automap_base(metadata=metadata)
        sql_load_mapped_base(MappedBase)

        for table_name, table in MappedBase.metadata.tables.items():
            if len(table.primary_key.columns) == 0 and table_name not in MappedBase.classes:
                logger.warning(
                    '[{}] Table "{}" does not have primary key and will be ignored'.format(id_short, table_name))

        result = {
            'engine': engine,
            'Session': Session,
            'MappedBase': MappedBase,
            'type_code_to_sql_type': type_code_to_sql_type,
            'default_timezone': default_timezone,
            'connect_time': connect_time,
            'reflect_time': reflect_time,
            'reflect_memory_usage_approx': reflect_memory_usage_approx,
            'reflect_metadata_dump': metadata_dump['file_path'] if metadata_dump else None
        }

    session.close()

    return result


def sql_build_engine_url(conf, tunnel=None):
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


def url_encode(value):
    return quote_plus(value)


def sql_create_connection_engine(conf, tunnel):
    engine_url = sql_build_engine_url(conf, tunnel)

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


def sql_load_mapped_base(MappedBase, clear=False):
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


def sql_load_database_table(engine, MappedBase, schema, table):
    bind = MappedBase.metadata.bind

    related_metadata = MetaData(schema=schema, bind=bind)
    related_metadata.reflect(bind=engine, schema=schema, only=[table])
    related_base = automap_base(metadata=related_metadata)
    sql_load_mapped_base(related_base)

    return related_base.classes.get(table)
