from sqlalchemy import inspect


def sql_inspect(cls):
    return inspect(cls)


def sql_get_session_engine(session):
    return session.bind.engine.name
