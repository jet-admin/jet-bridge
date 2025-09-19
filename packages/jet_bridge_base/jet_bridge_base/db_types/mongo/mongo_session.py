from .mongo_queryset import MongoQueryset
from .mongo_column import MongoColumn
from .mongo_declarative_meta import MongoDeclarativeMeta


class MongoSession(object):
    info = None
    records = None

    def __init__(self, db):
        self.db = db
        self.info = dict()
        self.records = list()

    def commit(self):
        for record in self.records:
            name = record.get_meta().table_name
            update_pending = record.get_update_pending()

            if record.is_delete_pending() and not record.is_create_pending():
                self.db[name].delete_one({'_id': record._id})
            elif record.is_create_pending():
                record_data = record.get_data()
                data = {}

                for key, value in record_data.items():
                    if key == '_id':
                        continue
                    data[key] = value

                self.db[name].insert_one(data)
            elif len(update_pending):
                record_data = record.get_data()
                data = {}

                for key, value in record_data.items():
                    if key not in update_pending:
                        continue
                    data[key] = value

                self.db[name].update_one({'_id': record._id}, {'$set': data})

            record.clear_pending()

    def rollback(self):
        pass

    def close(self):
        pass

    def query(self, *args):
        if isinstance(args[0], MongoDeclarativeMeta):
            name = args[0].get_name()
            select = None
        elif len(args) > 0 and all(map(lambda x: isinstance(x, MongoColumn), args)):
            name = args[0].table.name
            select = args
        else:
            raise Exception('Unsupported query args={}'.format(args))

        return MongoQueryset(self, name, select=select)

    def add(self, record):
        self.bind_record(record)
        record.mark_create()

    def delete(self, record):
        record.mark_delete()

    def bind_record(self, record):
        self.records.append(record)
