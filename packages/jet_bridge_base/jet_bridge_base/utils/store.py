import json
from sqlalchemy import create_engine

from jet_bridge_base import settings
from jet_bridge_base.encoders import JSONEncoder
from jet_bridge_base.logger import logger
from sqlalchemy.orm import scoped_session, sessionmaker


class Store(object):
    engine = None
    sessions = None

    def __init__(self, path):
        self.path = path
        self.open()

    def open(self):
        try:
            self.engine = create_engine('sqlite:///{}'.format(self.path))
            self.sessions = scoped_session(sessionmaker(self.engine))

            with self.sessions() as session:
                session.execute('CREATE TABLE IF NOT EXISTS kv_store (key text unique, value text)')
                session.commit()
        except Exception as e:
            logger.error('Store initialize failed', exc_info=e)

    def is_ok(self):
        return self.engine is not None and self.sessions is not None

    def close(self):
        if self.engine:
            self.engine.dispose()

    def get(self, key, default=None):
        if not self.is_ok():
            return default

        with self.sessions() as session:
            item = session.execute('SELECT value FROM kv_store WHERE key = :key', {'key': key}).fetchone()
            if item is None:
                return default
            return item[0]

    def set(self, key, value):
        if not self.is_ok():
            return

        with self.sessions() as session:
            session.execute('REPLACE INTO kv_store (key, value) VALUES (:key, :value)', {'key': key, 'value': value})
            session.commit()

    def get_object(self, key, default=None):
        data = self.get(key)

        if data is None:
            return default

        try:
            return json.loads(data)
        except ValueError:
            return default

    def set_object(self, key, value):
        data = json.dumps(value, cls=JSONEncoder)
        self.set(key, data)


store = Store(settings.STORE_PATH)
