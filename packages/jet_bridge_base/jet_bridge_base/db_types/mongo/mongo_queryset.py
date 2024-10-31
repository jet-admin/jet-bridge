import json
import re
import pymongo
from bson import ObjectId

from .common import mongo_inspect
from .mongo_operator import MongoOperator
from .mongo_record import MongoRecord
from .mongo_desc import MongoDesc


class MongoQueryset(object):
    select = None
    whereclause = None
    _joins = None
    _search = None
    _offset = None
    _limit = None
    _sort = None

    def __init__(self, session, name, select=None, whereclause=None, joins=None, search=None, offset=None, limit=None, sort=None):
        self.session = session
        self.db = session.db
        self.name = name
        self.query = self.db[self.name]
        self.select = select
        self.whereclause = whereclause
        self._joins = joins
        self._search = search
        self._offset = offset
        self._limit = limit
        self._sort = sort

    def to_internal_value(self, value, column):
        if isinstance(value, bytes) and column.params.get('type') == 'object_id':
            return ObjectId(value)
        else:
            return value

    def get_column_path(self, column):
        return '{}.{}'.format(column.table.name, column.name) if column.table.name != self.name else column.name

    def get_empty(self):
        return {
            '_id': {'$exists': False}
        }

    def map_operator(self, arg):
        acc = {}

        if isinstance(arg, MongoOperator):
            if arg.operator == '__eq__':
                column_path = self.get_column_path(arg.lhs)
                value = self.to_internal_value(arg.rhs, arg.lhs)
                acc[column_path] = value
            elif arg.operator == '__gt__':
                column_path = self.get_column_path(arg.lhs)
                value = self.to_internal_value(arg.rhs, arg.lhs)
                acc[column_path] = {'$gt': value}
            elif arg.operator == '__ge__':
                column_path = self.get_column_path(arg.lhs)
                value = self.to_internal_value(arg.rhs, arg.lhs)
                acc[column_path] = {'$gte': value}
            elif arg.operator == '__lt__':
                column_path = self.get_column_path(arg.lhs)
                value = self.to_internal_value(arg.rhs, arg.lhs)
                acc[column_path] = {'$lt': value}
            elif arg.operator == '__le__':
                column_path = self.get_column_path(arg.lhs)
                value = self.to_internal_value(arg.rhs, arg.lhs)
                acc[column_path] = {'$lte': value}
            elif arg.operator == 'exists':
                column_path = self.get_column_path(arg.lhs)
                value = self.to_internal_value(arg.rhs, arg.lhs)
                acc[column_path] = {'$exists': value}
            elif arg.operator == 'in':
                column_path = self.get_column_path(arg.lhs)
                value = self.to_internal_value(arg.rhs, arg.lhs)
                acc[column_path] = {'$in': value}
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
                column_path = self.get_column_path(arg.lhs)
                value = self.to_internal_value(arg.rhs, arg.lhs)
                acc[column_path] = {'$regex': self.get_regex_from_ilike(value)}

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
        if len(args) == 0:
            return self

        result = self.clone()

        for arg in args:
            if not result.whereclause:
                result.whereclause = []
            result.whereclause.append(self.map_operator(arg))

        return result

    def join(self, model, operator):
        result = self.clone()

        result._joins = result._joins or []
        result._joins.append((model, operator))

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
        if len(columns) == 0:
            return self

        result = self.clone()
        result._sort = result._sort or []

        for item in columns:
            if isinstance(item, MongoDesc):
                result._sort.append((item.column.name, pymongo.DESCENDING))
            else:
                result._sort.append((item.name, pymongo.ASCENDING))

        return result

    def get_order_by(self):
        return self._sort

    def clone(self):
        return MongoQueryset(self.session, self.name, select=self.select, whereclause=self.whereclause,
                             joins=self._joins, search=self._search, offset=self._offset, limit=self._limit,
                             sort=self._sort)

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

    def get_aggregate_pipeline(self, limit=None):
        aggregate = []

        if self._joins:
            for model, operator in self._joins:
                mapper = mongo_inspect(model)
                aggregate.append({'$lookup': {
                    'from': mapper.selectable.name,
                    'localField': operator.rhs.name,
                    'foreignField': operator.lhs.name,
                    'as': mapper.selectable.name
                }})

        filters = self.get_filters()
        if filters:
            aggregate.append({'$match': filters})

        if self._sort:
            aggregate.append({'$sort': dict(self._sort)})

        if self._offset:
            aggregate.append({'$skip': self._offset})

        if limit is not None:
            aggregate.append({'$limit': limit})
        elif self._limit:
            aggregate.append({'$limit': self._limit})

        if self.select:
            aggregate.append({'$project': dict(map(lambda x: (x.name, 1), self.select))})

        return aggregate

    def all(self):
        pipeline = self.get_aggregate_pipeline()
        for data in self.query.aggregate(pipeline, allowDiskUse=True):
            record = MongoRecord(self.name, **data)
            self.session.bind_record(record)

            yield record

    def count(self):
        pipeline = self.get_aggregate_pipeline()
        pipeline.append({'$count': 'count'})

        try:
            result = self.query.aggregate(pipeline, allowDiskUse=True).next()
            return result['count']
        except StopIteration:
            return 0

    def estimated_document_count(self):
        return self.query.estimated_document_count()

    def first(self):
        pipeline = self.get_aggregate_pipeline(limit=1)

        try:
            data = self.query.aggregate(pipeline, allowDiskUse=True).next()
        except StopIteration:
            return None

        record = MongoRecord(self.name, **data)
        self.session.bind_record(record)

        return record

    def one(self):
        return self.first()

    def aggregate(self, pipeline):
        filters = self.get_filters()

        try:
            return self.query.aggregate([{'$match': filters}, pipeline]).next()
        except StopIteration:
            return {'aggregation': 0}

    def group(self, pipeline, sort):
        filters = self.get_filters()
        return list(self.query.aggregate([{'$match': filters}, pipeline, sort]))

    def __iter__(self):
        return self.all()

    def __repr__(self):
        return json.dumps({
            'whereclause': list(map(lambda x: repr(x), self.whereclause)) if self.whereclause else None,
            '_search': self._search,
            '_offset': self._offset,
            '_limit': self._limit,
            '_sort': self._sort,
        })
