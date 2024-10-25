from .mongo_declarative_meta import MongoDeclarativeMeta


class MongoBaseClasses(dict):
    def __init__(self, tables, *args, **kwargs):
        super(MongoBaseClasses, self).__init__(*args, **kwargs)

        for table in tables:
            self[table.name] = MongoDeclarativeMeta(table)

    def __iter__(self):
        for value in self.values():
            yield value


class MongoBase(object):
    def __init__(self, metadata):
        self.metadata = metadata
        self.classes = MongoBaseClasses(metadata.tables)
