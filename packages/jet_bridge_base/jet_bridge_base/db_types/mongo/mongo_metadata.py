from .mongo_table import MongoTable


class MongoMetadata(object):
    def __init__(self, tables=None, schema=None):
        self.tables = list(map(lambda x: MongoTable.deserialize(x), tables)) if tables else list()
        self.schema = schema

    def append_table(self, table):
        self.tables.append(table)

    @staticmethod
    def deserialize(obj):
        return MongoMetadata(**obj)

    def serialize(self):
        return {
            'tables': list(map(lambda x: x.serialize(), self.tables)),
            'schema': self.schema
        }
