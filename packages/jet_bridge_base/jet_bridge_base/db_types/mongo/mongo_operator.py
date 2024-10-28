import json


class MongoOperator(object):
    def __init__(self, operator, lhs=None, rhs=None):
        self.operator = operator
        self.lhs = lhs
        self.rhs = rhs

    def __invert__(self):
        return MongoOperator('not', self)

    def __repr__(self):
        return json.dumps({
            'operator': self.operator,
            'lhs': repr(self.lhs),
            'rhs': repr(self.rhs),
        })
