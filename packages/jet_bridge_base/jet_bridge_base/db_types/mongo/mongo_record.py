class MongoRecordMeta(object):
    def __init__(self, table_name):
        self.table_name = table_name


class MongoRecord(object):
    create_pending = False
    delete_pending = False

    def __init__(self, table_name, **kwargs):
        object.__setattr__(self, 'meta', MongoRecordMeta(table_name))
        object.__setattr__(self, 'data', dict(kwargs))
        object.__setattr__(self, 'update_pending', set())

    def __getattribute__(self, name):
        if name in ['meta', 'data']:
            data = super().__getattribute__('data')
            return data.get(name, None)
        else:
            return super().__getattribute__(name)

    def __getattr__(self, name):
        return self.get(name)

    def get(self, name, default=None):
        data = super().__getattribute__('data')
        return data.get(name, default)

    def __setattr__(self, name, value):
        self.set(name, value)

    def set(self, name, value):
        data = super().__getattribute__('data')
        data[name] = value
        self.mark_update(name)

    def get_data(self):
        return object.__getattribute__(self, 'data')

    def get_meta(self):
        return object.__getattribute__(self, 'meta')

    def is_create_pending(self):
        return object.__getattribute__(self, 'create_pending')

    def mark_create(self):
        object.__setattr__(self, 'create_pending', True)

    def get_update_pending(self):
        return object.__getattribute__(self, 'update_pending')

    def mark_update(self, name):
        object.__getattribute__(self, 'update_pending').add(name)

    def is_delete_pending(self):
        return object.__getattribute__(self, 'delete_pending')

    def mark_delete(self):
        object.__setattr__(self, 'delete_pending', True)

    def clear_pending(self):
        object.__setattr__(self, 'create_pending', False)
        object.__getattribute__(self, 'update_pending').clear()
        object.__setattr__(self, 'delete_pending', False)

    def __repr__(self):
        return '_id({})'.format(self.get('_id'))
