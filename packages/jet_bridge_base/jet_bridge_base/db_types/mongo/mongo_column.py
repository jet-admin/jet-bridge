from .mongo_operator import MongoOperator


class MongoColumn(object):
    def __init__(self, table, name, type, nullable=True, mixed_types=None, autoincrement=False, default=None,
                 server_default=None, foreign_keys=None, comment=None, params=None):
        self.table = table
        self.name = name
        self.key = name
        self.type = type
        self.nullable = nullable
        self.mixed_types = mixed_types
        self.autoincrement = autoincrement
        self.default = default
        self.server_default = server_default
        self.foreign_keys = foreign_keys or list()
        self.comment = comment
        self.params = params or dict()

    @staticmethod
    def deserialize(table, obj):
        name = obj.pop('name')
        type = obj.pop('type')
        return MongoColumn(table, name, type, **obj)

    def serialize(self):
        return {
            'name': self.name,
            'type': self.type,
            'nullable': self.nullable,
            'mixed_types': self.mixed_types,
            'autoincrement': self.autoincrement,
            'default': self.default,
            'server_default': self.server_default,
            'foreign_keys': self.foreign_keys,
            'comment': self.comment,
            'params': self.params
        }

    def __eq__(self, other):
        return MongoOperator('__eq__', self, other)

    def __gt__(self, other):
        return MongoOperator('__gt__', self, other)

    def __ge__(self, other):
        return MongoOperator('__ge__', self, other)

    def __lt__(self, other):
        return MongoOperator('__lt__', self, other)

    def __le__(self, other):
        return MongoOperator('__le__', self, other)

    # def __invert__(self):
    #     return MongoOperator('not', self)

    def ilike(self, value):
        return MongoOperator('ilike', self, value)

    def exists(self, value):
        return MongoOperator('exists', self, value)

    def __repr__(self):
        return '{}.{}'.format(self.table.name, self.name)
