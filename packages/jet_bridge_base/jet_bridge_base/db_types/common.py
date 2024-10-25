from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeMeta

from .mongo import MongoDeclarativeMeta, MongoSession


def inspect_uniform(cls):
    if isinstance(cls, DeclarativeMeta):
        return inspect(cls)
    elif isinstance(cls, MongoDeclarativeMeta):
        return getattr(cls, '_mapper')


def get_session_engine(session):
    if isinstance(session, MongoSession):
        return 'mongo'
    else:
        return session.bind.engine.name
