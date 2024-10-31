import os
import pickle

from jet_bridge_base import settings
from jet_bridge_base.logger import logger
from jet_bridge_base.utils.conf import get_connection_id, get_connection_schema, get_connection_name, get_metadata_file_path


def sql_dump_metadata_file(conf, metadata):
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


def sql_load_metadata_file(conf, connection):
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
