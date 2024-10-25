from jet_bridge_base.utils.common import CollectionDict


class MongoMapper(object):
    def __init__(self, table):
        self.tables = [table]
        self.relationships = CollectionDict()
        self.selectable = table
        self.primary_key = [table.columns['_id']]
        self.columns = table.columns
