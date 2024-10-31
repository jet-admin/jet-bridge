from .mongo_mapper import MongoMapper
from .mongo_record import MongoRecord


class MongoDeclarativeMeta(object):
    def __init__(self, table):
        self._mapper = MongoMapper(table)

        for column in table.columns:
            setattr(self, column.name, column)

    def get_name(self):
        return self._mapper.selectable.name

    def __call__(self, **kwargs):
        table_name = self._mapper.selectable.name
        return MongoRecord(table_name, **kwargs)

    def __repr__(self):
        return self.get_name()
