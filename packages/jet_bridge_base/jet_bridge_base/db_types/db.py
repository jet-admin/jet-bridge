from .mongo import mongodb_init_database_connection, MongoBase, mongo_load_mapped_base
from .sql import sql_init_database_connection, sql_load_mapped_base


def init_database_connection(conf, tunnel, id_short, connection_name, schema, pending_connection):
    if conf.get('engine') == 'mongo':
        return mongodb_init_database_connection(
            conf,
            tunnel,
            id_short,
            connection_name,
            schema,
            pending_connection
        )
    else:
        return sql_init_database_connection(
            conf,
            tunnel,
            id_short,
            connection_name,
            schema,
            pending_connection
        )


def load_mapped_base(MappedBase, clear=False):
    if isinstance(MappedBase, MongoBase):
        mongo_load_mapped_base(MappedBase, clear)
    else:
        sql_load_mapped_base(MappedBase, clear)
