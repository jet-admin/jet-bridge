import logging

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker, scoped_session

# try:
#     from geoalchemy2 import types
# except ImportError:
#     pass

from jet_bridge_base import settings
from jet_bridge_base.models import Base


def build_engine_url():
    if not settings.DATABASE_ENGINE or not settings.DATABASE_NAME:
        return

    url = [
        settings.DATABASE_ENGINE,
        '://'
    ]

    if settings.DATABASE_USER:
        url.append(settings.DATABASE_USER)

        if settings.DATABASE_PASSWORD:
            url.append(':')
            url.append(settings.DATABASE_PASSWORD)

        if settings.DATABASE_HOST:
            url.append('@')

    if settings.DATABASE_HOST:
        url.append(settings.DATABASE_HOST)

        if settings.DATABASE_PORT:
            url.append(':')
            url.append(settings.DATABASE_PORT)

        url.append('/')

    if settings.DATABASE_ENGINE == 'sqlite':
        url.append('/')

    url.append(settings.DATABASE_NAME)

    if settings.DATABASE_EXTRA:
        url.append(settings.DATABASE_EXTRA)
    elif settings.DATABASE_ENGINE == 'mysql':
        url.append('?charset=utf8')
    elif settings.DATABASE_ENGINE == 'mssql+pyodbc':
        url.append('?driver=SQL+Server+Native+Client+11.0')

    return ''.join(url)

engine_url = build_engine_url()
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
