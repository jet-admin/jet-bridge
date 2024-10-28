import json
import re
import pymongo
from bson import ObjectId

from .mongo_operator import MongoOperator
from .mongo_record import MongoRecord

from .mongo_desc import MongoDesc


class MongoQueryset(object):
    select = None
    whereclause = None
    _search = None
    _offset = None
    _limit = None
    _sort = None

    def __init__(self, session, name, select=None, whereclause=None, search=None, offset=None, limit=None, sort=None):
        self.session = session
        self.db = session.db
        self.name = name
        self.query = self.db[self.name]
        self.select = select
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

    def get_empty(self):
        return {
            '_id': {'$exists': False}
        }

    def map_operator(self, arg):
        acc = {}

        if isinstance(arg, MongoOperator):
            if arg.operator == '__eq__':
                acc[arg.lhs.name] = self.to_internal_value(arg.rhs, arg.lhs)
            elif arg.operator == '__gt__':
                acc[arg.lhs.name] = {'$gt': self.to_internal_value(arg.rhs, arg.lhs)}
            elif arg.operator == '__ge__':
                acc[arg.lhs.name] = {'$gte': self.to_internal_value(arg.rhs, arg.lhs)}
            elif arg.operator == '__lt__':
                acc[arg.lhs.name] = {'$lt': self.to_internal_value(arg.rhs, arg.lhs)}
            elif arg.operator == '__le__':
                acc[arg.lhs.name] = {'$lte': self.to_internal_value(arg.rhs, arg.lhs)}
            elif arg.operator == 'exists':
                acc[arg.lhs.name] = {'$exists': self.to_internal_value(arg.rhs, arg.lhs)}
            elif arg.operator == 'in':
                acc[arg.lhs.name] = {'$in': self.to_internal_value(arg.rhs, arg.lhs)}
            elif arg.operator == 'json_icontains':
                acc.update(self.get_empty())
            elif arg.operator == 'not':
                positive = self.map_operator(arg.lhs)
                for key, value in positive.items():
                    if isinstance(value, dict):
                        acc[key] = {'$not': value}
                    else:
                        acc[key] = {'$ne': value}
            elif arg.operator == 'ilike':
                value = self.to_internal_value(arg.rhs, arg.lhs)
                acc[arg.lhs.name] = {'$regex': self.get_regex_from_ilike(value)}

        return acc

    def get_regex_from_ilike(self, value):
        if not isinstance(value, str):
            return None

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

        return re.compile(prefix + re.escape(value) + postfix, re.IGNORECASE)

    def filter(self, *args):
        result = self.clone()

        for arg in args:
            if not result.whereclause:
                result.whereclause = []
            result.whereclause.append(self.map_operator(arg))

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
        return MongoQueryset(self.session, self.name, select=self.select, whereclause=self.whereclause,
                             search=self._search, offset=self._offset, limit=self._limit, sort=self._sort)

    def get_filters(self):
        filters = []

        if self.whereclause:
            filters.extend(self.whereclause)

        if self._search is not None:
            filters.append({'$text': {'$search': self._search}})

        if len(filters) > 1:
            return {'$and': filters}
        elif len(filters) == 1:
            return filters[0]
        else:
            return {}

    def first(self):
        filters = self.get_filters()
        data = self.query.find_one(
            **({'projection': list(map(lambda x: x.name, self.select))} if self.select else {}),
            filter=filters,
        )

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
        for data in self.query.find(
                **({'projection': list(map(lambda x: x.name, self.select))} if self.select else {}),
                filter=filters,
                **({'skip': self._offset} if self._offset else {}),
                **({'limit': self._limit} if self._limit else {}),
                sort=self._sort,
                allow_disk_use=True
        ):
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
