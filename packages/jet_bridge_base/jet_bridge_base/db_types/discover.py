from pymongo import MongoClient
from sqlalchemy import MetaData, inspection
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql.base import _bind_or_error

from jet_bridge_base.db_types.sql import sql_create_connection_engine, sql_get_tables
from jet_bridge_base.utils.conf import get_connection_schema


def discover_connection(conf, tunnel):
    bind = None
    client = None

    try:
        if conf.get('engine') == 'mongo':
            database_url = conf.get('url')
            database_name = conf.get('name')

            client = MongoClient(database_url, authSource=database_name)

            if database_name not in client.list_database_names():
                raise Exception('No such database found: {}'.format(database_name))

            db = client[conf.get('name')]
            db.list_collection_names()

            return True
        else:
            bind = sql_create_connection_engine(conf, tunnel)

            Session = scoped_session(sessionmaker(bind=bind))
            session = Session()

            with session.connection():
                return True
    except Exception as e:
        raise e
    finally:
        if bind:
            bind.dispose()

        if client:
            client.close()

        if tunnel:
            tunnel.close()


def discover_tables(conf, tunnel):
    bind = None
    client = None

    try:
        if conf.get('engine') == 'mongo':
            database_url = conf.get('url')
            database_name = conf.get('name')

            client = MongoClient(database_url, authSource=database_name)

            if database_name not in client.list_database_names():
                raise Exception('No such database found: {}'.format(database_name))

            db = client[conf.get('name')]

            return db.list_collection_names()
        else:
            schema = get_connection_schema(conf)
            bind = sql_create_connection_engine(conf, tunnel)

            Session = scoped_session(sessionmaker(bind=bind))
            session = Session()

            with session.connection() as connection:
                metadata = MetaData(schema=schema, bind=connection)

                if bind is None:
                    bind = _bind_or_error(metadata)

                with inspection.inspect(bind)._inspection_context() as insp:
                    if schema is None:
                        schema = metadata.schema

                    load, view_names = sql_get_tables(insp, metadata, bind, schema, foreign=True, views=True)
                    return load
    except Exception as e:
        raise e
    finally:
        if bind:
            bind.dispose()

        if client:
            client.close()

        if tunnel:
            tunnel.close()
