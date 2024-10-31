def mongo_inspect(cls):
    return getattr(cls, '_mapper')
