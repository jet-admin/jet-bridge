
class Adapter(object):

    def __init__(self, engine, session):
        self.engine = engine
        self.session = session

registered_adapters = {}
