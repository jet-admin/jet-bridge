

class Adapter(object):
    data_types = []

    def __init__(self, engine, session):
        self.engine = engine
        self.session = session

    def map_data_type(self, value):
        for rule in self.data_types:
            if rule['operator'] == 'equals' and value == rule['query']:
                return rule['date_type']
            elif rule['operator'] == 'startswith' and value[:len(rule['query'])] == rule['query']:
                return rule['date_type']

    def get_tables(self):
        raise NotImplementedError

registered_adapters = {}
