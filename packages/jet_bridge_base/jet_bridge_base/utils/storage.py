import dbm
import json

from jet_bridge_base import settings
from jet_bridge_base.encoders import JSONEncoder


class Storage(object):
    db = None

    def __init__(self, path):
        self.path = path

        try:
            self.db = self.open_db()
        except Exception:
            self.db = None

    def is_ok(self):
        return self.db is not None

    def open_db(self):
        return dbm.open(self.path, 'c')

    def get(self, key, default=None):
        if not self.db:
            return
        return self.db.get(key, default)

    def set(self, key, value):
        if not self.db:
            return
        self.db[key] = value

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


storage = Storage(settings.STORE_PATH)
