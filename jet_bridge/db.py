import logging
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

from jet_bridge import settings
from jet_bridge.models import Base


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
            url.append(str(settings.DATABASE_PORT))

        url.append('/')

    url.append(settings.DATABASE_NAME)

    return ''.join(url)

engine_url = build_engine_url()
Session = None

if engine_url:
    engine = create_engine(engine_url)
    Session = sessionmaker(bind=engine)

    logging.info('Connected to database engine "{}" with name "{}"'.format(settings.DATABASE_ENGINE, settings.DATABASE_NAME))

    Base.metadata.create_all(engine)

    metadata = MetaData()
    metadata.reflect(engine)
    MappedBase = automap_base(metadata=metadata)
    MappedBase.prepare()
