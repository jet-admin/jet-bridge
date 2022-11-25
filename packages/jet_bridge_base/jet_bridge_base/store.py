from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from jet_bridge_base import settings
from jet_bridge_base.logger import logger
from jet_bridge_base.models.base import Base


class Store(object):
    engine = None
    sessions = None

    def __init__(self, path, base):
        self.path = path
        self.base = base
        self.open()

    def open(self):
        try:
            self.engine = create_engine('sqlite:///{}'.format(self.path))
            self.sessions = scoped_session(sessionmaker(self.engine))

            import jet_bridge_base.models
            Base.metadata.create_all(self.engine)
        except Exception as e:
            logger.error('Store initialize failed', exc_info=e)

    def close(self):
        if self.engine:
            self.engine.dispose()

    def is_ok(self):
        return self.engine is not None and self.sessions is not None

    def session(self):
        return self.sessions()


store = Store(settings.STORE_PATH, Base)
