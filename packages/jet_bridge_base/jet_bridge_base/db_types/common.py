from sqlalchemy.orm import DeclarativeMeta, aliased

from .mongo import MongoDeclarativeMeta, MongoSession, mongo_inspect
from .sql import sql_inspect, sql_get_session_engine


def inspect_uniform(cls):
    if isinstance(cls, DeclarativeMeta):
        return sql_inspect(cls)
    elif isinstance(cls, MongoDeclarativeMeta):
        return mongo_inspect(cls)


def aliased_uniform(cls):
    if isinstance(cls, DeclarativeMeta):
        return aliased(cls)
    elif isinstance(cls, MongoDeclarativeMeta):
        return cls


def get_session_engine(session):
    if isinstance(session, MongoSession):
        return 'mongo'
    else:
        return sql_get_session_engine(session)
