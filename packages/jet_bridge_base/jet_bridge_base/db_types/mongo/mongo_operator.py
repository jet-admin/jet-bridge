class MongoOperator(object):
    def __init__(self, operator, lhs=None, rhs=None):
        self.operator = operator
        self.lhs = lhs
        self.rhs = rhs
