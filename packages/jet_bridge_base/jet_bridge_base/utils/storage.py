import dbm
import json

from jet_bridge_base import settings
from jet_bridge_base.encoders import JSONEncoder


class Storage(object):
    def __init__(self, path):
        self.path = path

    def is_ok(self):
        try:
            with self.get_file():
                return True
        except Exception:
            return False

    def get_file(self):
        return dbm.open(self.path, 'c')

    def get(self, key, default=None):
        with self.get_file() as f:
            return f.get(key, default)

    def set(self, key, value):
        with self.get_file() as f:
            f[key] = value

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
