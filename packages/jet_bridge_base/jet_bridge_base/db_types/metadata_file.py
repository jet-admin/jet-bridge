import os

from jet_bridge_base import settings
from jet_bridge_base.logger import logger
from jet_bridge_base.utils.conf import get_connection_id, get_connection_schema, get_connection_name, \
    get_metadata_file_path

from .mongo import mongo_dump_metadata_file, MongoMetadata
from .sql import sql_dump_metadata_file


def dump_metadata_file(conf, metadata):
    if isinstance(metadata, MongoMetadata):
        mongo_dump_metadata_file(conf, metadata)
    else:
        sql_dump_metadata_file(conf, metadata)


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
