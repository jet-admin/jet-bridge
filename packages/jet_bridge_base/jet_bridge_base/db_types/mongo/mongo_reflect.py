import time
from datetime import datetime
from bson import ObjectId

from jet_bridge_base.logger import logger
from jet_bridge_base.models import data_types
from jet_bridge_base.utils.process import get_memory_usage_human

from .mongo_column import MongoColumn
from .mongo_table import MongoTable
from .mongo_metadata import MongoMetadata


def reflect_mongodb(
    cid_short,
    db,
    only=None,
    max_read_records=1000000,
    pending_connection=None
):
    available = db.list_collection_names()

    if only is None:
        load = available
    elif callable(only):
        load = [name for name in available if only(name)]
    else:
        load = [name for name in only]

    metadata = MongoMetadata()

    if pending_connection:
        pending_connection['tables_total'] = len(load)

    i = 0
    for name in load:
        # Wait to allow other threads execution
        time.sleep(0.01)

        logger.info('[{}] Analyzing collection "{}" ({} / {})" (Mem:{})...'.format(
            cid_short, name, i + 1, len(load), get_memory_usage_human())
        )

        page = 1
        limit = 10000
        table = MongoTable(name)

        while True:
            skip = (page - 1) * limit
            items = db[name].find(skip=skip, limit=limit)
            has_items = False

            for item in items:
                has_items = True

                for key, value in item.items():
                    if value is None and key in table.columns:
                        continue

                    field_type = None
                    field_params = None

                    if value is None and key not in table.columns:
                        # field_type = None
                        pass
                    if isinstance(value, int):
                        field_type = data_types.INTEGER
                    elif isinstance(value, str):
                        # field_type = data_types.TEXT
                        field_type = data_types.CHAR
                    elif isinstance(value, float):
                        field_type = data_types.FLOAT
                    elif isinstance(value, bool):
                        field_type = data_types.BOOLEAN
                    elif isinstance(value, datetime):
                        field_type = data_types.DATE_TIME
                    elif isinstance(value, dict):
                        field_type = data_types.JSON
                    elif isinstance(value, list):
                        field_type = data_types.JSON
                    elif isinstance(value, ObjectId) or type(value) is ObjectId:
                        field_type = data_types.BINARY
                        field_params = {'type': 'object_id'}
                    else:
                        field_type = data_types.TEXT

                    if key in table.columns:
                        column = table.columns[key]
                    else:
                        column = MongoColumn(table, key, None)
                        table.append_column(column)

                    if column.type and column.type != field_type:
                        column.mixed_types = column.mixed_types or set()
                        column.mixed_types.add(column.type)
                        column.mixed_types.add(field_type)

                    column.type = field_type

                    if field_params:
                        column.params = field_params

            if has_items and skip + limit < max_read_records:
                page += 1
            else:
                break

        for column in table.columns:
            if column.type is None:
                column.type = data_types.CHAR

            if column.mixed_types:
                column.type = data_types.JSON

                logger.info('Field "{}"."{}" has data stored in multiple types ({}), falling back to JSON'.format(
                    name,
                    column.name,
                    ','.join(column.mixed_types)
                ))

        metadata.append_table(table)

        i += 1

        if pending_connection:
            pending_connection['tables_processed'] = i

    return metadata
