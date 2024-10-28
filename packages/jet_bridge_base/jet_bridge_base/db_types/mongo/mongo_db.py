import time

from jet_bridge_base.logger import logger
from jet_bridge_base.utils.conf import get_connection_only_predicate
from jet_bridge_base.utils.process import get_memory_usage, get_memory_usage_human

from .mongo_session import MongoSession
from .mongo_metadata_file import mongo_load_metadata_file, mongo_dump_metadata_file
from .mongo_reflect import reflect_mongodb
from .mongo_base import MongoBase
from .mongo_engine import MongoEngine


def mongodb_init_database_connection(conf, tunnel, id_short, connection_name, schema, pending_connection):
    engine = MongoEngine()
    pending_connection['engine'] = engine

    logger.info('[{}] Connecting to database "{}"...'.format(id_short, connection_name))

    connect_start = time.time()

    database_url = conf.get('url')
    database_name = conf.get('name')

    engine.connect(database_url)
    db = engine.get_db(database_name)
    Session = lambda: MongoSession(db)

    connect_end = time.time()
    connect_time = round(connect_end - connect_start, 3)

    default_timezone = None
    # default_timezone = fetch_default_timezone(session)
    # if default_timezone is not None:
    #     logger.info('[{}] Default timezone detected: "{}"'.format(id_short, default_timezone))
    # else:
    #     logger.info('[{}] Failed to detect default timezone'.format(id_short))

    metadata_dump = mongo_load_metadata_file(conf)

    if metadata_dump:
        metadata = metadata_dump['metadata']

        reflect_time = None
        reflect_memory_usage_approx = None

        logger.info('[{}] Loaded schema cache for "{}"'.format(id_short, connection_name))
    else:
        logger.info('[{}] Getting schema for "{}"...'.format(id_short, connection_name))

        reflect_start_time = time.time()
        reflect_start_memory_usage = get_memory_usage()

        only = get_connection_only_predicate(conf)
        metadata = reflect_mongodb(id_short, db, only=only, pending_connection=pending_connection)

        reflect_end_time = time.time()
        reflect_end_memory_usage = get_memory_usage()
        reflect_time = round(reflect_end_time - reflect_start_time, 3)
        reflect_memory_usage_approx = reflect_end_memory_usage - reflect_start_memory_usage

        mongo_dump_metadata_file(conf, metadata)

    logger.info('[{}] Connected to "{}" (Mem:{})'.format(id_short, connection_name, get_memory_usage_human()))

    MappedBase = MongoBase(metadata)

    result = {
        'engine': engine,
        'Session': Session,
        'MappedBase': MappedBase,
        'default_timezone': default_timezone,
        'connect_time': connect_time,
        'reflect_time': reflect_time,
        'reflect_memory_usage_approx': reflect_memory_usage_approx,
        'reflect_metadata_dump': metadata_dump['file_path'] if metadata_dump else None
    }

    return result


def mongo_load_mapped_base(MappedBase, clear=False):
    raise NotImplementedError
