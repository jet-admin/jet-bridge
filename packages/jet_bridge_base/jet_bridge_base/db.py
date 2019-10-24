import logging

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker, scoped_session

try:
    from geoalchemy2 import types
except ImportError:
    pass

from jet_bridge_base import settings
from jet_bridge_base.models import Base


def build_engine_url(
        DATABASE_ENGINE,
        DATABASE_HOST,
        DATABASE_PORT,
        DATABASE_NAME,
        DATABASE_USER,
        DATABASE_PASSWORD,
        DATABASE_EXTRA=''
):
    if not DATABASE_ENGINE or not DATABASE_NAME:
        return

    url = [
        DATABASE_ENGINE,
        '://'
    ]

    if DATABASE_USER:
        url.append(DATABASE_USER)

        if DATABASE_PASSWORD:
            url.append(':')
            url.append(DATABASE_PASSWORD)

        if DATABASE_HOST:
            url.append('@')

    if DATABASE_HOST:
        url.append(DATABASE_HOST)

        if DATABASE_PORT:
            url.append(':')
            url.append(DATABASE_PORT)

        url.append('/')

    if DATABASE_ENGINE == 'sqlite':
        url.append('/')

    url.append(DATABASE_NAME)

    if DATABASE_EXTRA:
        url.append(DATABASE_EXTRA)
    elif DATABASE_ENGINE == 'mysql':
        url.append('?charset=utf8')
    elif DATABASE_ENGINE == 'mssql+pyodbc':
        url.append('?driver=SQL+Server+Native+Client+11.0')

    return ''.join(url)


def build_engine_url_from_settings():
    return build_engine_url(
        settings.DATABASE_ENGINE,
        settings.DATABASE_HOST,
        settings.DATABASE_PORT,
        settings.DATABASE_NAME,
        settings.DATABASE_USER,
        settings.DATABASE_PASSWORD,
        settings.DATABASE_EXTRA
    )


engine_url = build_engine_url_from_settings()
Session = None

if engine_url:
    if settings.DATABASE_ENGINE == 'sqlite':
        engine = create_engine(engine_url)
    else:
        engine = create_engine(engine_url, pool_size=settings.DATABASE_CONNECTIONS, max_overflow=10, pool_recycle=1)

    Session = scoped_session(sessionmaker(bind=engine))

    logging.info('Connected to database engine "{}" with name "{}"'.format(settings.DATABASE_ENGINE, settings.DATABASE_NAME))

    Base.metadata.create_all(engine)

    metadata = MetaData()
    metadata.reflect(engine)
    MappedBase = automap_base(metadata=metadata)

    def name_for_scalar_relationship(base, local_cls, referred_cls, constraint):
        return referred_cls.__name__.lower() + '_relation'

    MappedBase.prepare(name_for_scalar_relationship=name_for_scalar_relationship)
