import json
import re
import pymongo
from bson import ObjectId

from .mongo_operator import MongoOperator
from .mongo_record import MongoRecord

from .mongo_desc import MongoDesc


class MongoQueryset(object):
    whereclause = None
    _search = None
    _offset = None
    _limit = None
    _sort = None

    def __init__(self, session, name, whereclause=None, search=None, offset=None, limit=None, sort=None):
        self.session = session
        self.db = session.db
        self.name = name
        self.query = self.db[self.name]
        self.whereclause = whereclause
        self._search = search
        self._offset = offset
        self._limit = limit
        self._sort = sort

    def to_internal_value(self, value, column):
        if isinstance(value, bytes) and column.params.get('type') == 'object_id':
            return ObjectId(value)
        else:
            return value

    def filter(self, arg):
        result = self.clone()
        result.whereclause = result.whereclause = {}

        if isinstance(arg, MongoOperator):
            if arg.operator == '__eq__':
                result.whereclause[arg.lhs.name] = self.to_internal_value(arg.rhs, arg.lhs)
            elif arg.operator == '__gt__':
                result.whereclause[arg.lhs.name] = {'$gt': self.to_internal_value(arg.rhs, arg.lhs)}
            elif arg.operator == '__ge__':
                result.whereclause[arg.lhs.name] = {'$gte': self.to_internal_value(arg.rhs, arg.lhs)}
            elif arg.operator == '__lt__':
                result.whereclause[arg.lhs.name] = {'$lt': self.to_internal_value(arg.rhs, arg.lhs)}
            elif arg.operator == '__le__':
                result.whereclause[arg.lhs.name] = {'$lte': self.to_internal_value(arg.rhs, arg.lhs)}
            elif arg.operator == 'exists':
                result.whereclause[arg.lhs.name] = {'$exists': self.to_internal_value(arg.rhs, arg.lhs)}
            elif arg.operator == 'ilike':
                value = self.to_internal_value(arg.rhs, arg.lhs)

                if value.startswith('%'):
                    value = value[1:]
                    prefix = ''
                else:
                    prefix = '^'

                if value.endswith('%'):
                    value = value[:-1]
                    postfix = ''
                else:
                    postfix = '$'

                regex = re.compile(prefix + re.escape(value) + postfix, re.IGNORECASE)
                result.whereclause[arg.lhs.name] = {'$regex': regex}

        return result

    def search(self, search):
        result = self.clone()
        result._search = search
        return result

    def offset(self, offset):
        result = self.clone()
        result._offset = offset
        return result

    def limit(self, limit):
        result = self.clone()
        result._limit = limit
        return result

    def get_limit(self):
        return self._limit

    def order_by(self, *columns):
        result = self.clone()

        def map_sort(item):
            if isinstance(item, MongoDesc):
                return (item.column.name, pymongo.DESCENDING)
            else:
                return (item.name, pymongo.ASCENDING)

        result._sort = list(map(map_sort, columns))
        return result

    def get_order_by(self):
        return self._sort

    def clone(self):
        return MongoQueryset(self.session, self.name, whereclause=self.whereclause, search=self._search, offset=self._offset,
                             limit=self._limit, sort=self._sort)

    def get_filters(self):
        filters = {
            **(self.whereclause if self.whereclause else {})
        }

        if self._search is not None:
            filters['$text'] = {'$search': self._search}

        return filters

    def first(self):
        filters = self.get_filters()
        data = self.query.find_one(filter=filters)

        if data is None:
            return None

        record = MongoRecord(self.name, **data)
        self.session.bind_record(record)

        return record

    def one(self):
        return self.first()

    def aggregate(self, pipeline):
        filters = self.get_filters()
        return self.query.aggregate([{'$match': filters}, pipeline]).next()

    def group(self, pipeline, sort):
        filters = self.get_filters()
        return list(self.query.aggregate([{'$match': filters}, pipeline, sort]))

    def __iter__(self):
        filters = self.get_filters()
        for data in self.query.find(filter=filters, skip=self._offset, limit=self._limit, sort=self._sort):
            record = MongoRecord(self.name, **data)
            self.session.bind_record(record)

            yield record

    def count(self):
        filters = self.get_filters()
        return self.query.count_documents(filters)

    def estimated_document_count(self):
        return self.query.estimated_document_count()

    def __repr__(self):
        return json.dumps({
            'whereclause': list(map(lambda x: repr(x), self.whereclause)) if self.whereclause else None,
            '_search': self._search,
            '_offset': self._offset,
            '_limit': self._limit,
            '_sort': self._sort,
        })
