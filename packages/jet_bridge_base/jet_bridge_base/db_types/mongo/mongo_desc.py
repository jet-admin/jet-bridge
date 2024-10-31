class MongoDesc(object):
    def __init__(self, column):
        self.column = column

    def __repr__(self):
        return 'desc({})'.format(repr(self.column))
