

class Adapter(object):

    def __init__(self, engine, session):
        self.engine = engine
        self.session = session

    def get_tables(self):
        raise NotImplementedError

registered_adapters = {}
