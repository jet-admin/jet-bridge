from jet_bridge_base.utils.common import CollectionDict

from .mongo_column import MongoColumn


class MongoTable(object):
    def __init__(self, name, columns=None, comment=None, schema=None):
        self.name = name
        self.columns = CollectionDict(map(lambda x: (
            x['name'],
            MongoColumn.deserialize(self, x)
        ), columns)) if columns else CollectionDict()
        self.comment = comment
        self.schema = schema

    def append_column(self, column):
        self.columns[column.name] = column

    @staticmethod
    def deserialize(obj):
        name = obj.pop('name')
        return MongoTable(name, **obj)

    def serialize(self):
        return {
            'name': self.name,
            'columns': list(map(lambda x: x.serialize(), self.columns.values())),
            'comment': self.comment,
            'schema': self.schema
        }
