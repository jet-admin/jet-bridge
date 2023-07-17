from sqlalchemy.ext import automap
from sqlalchemy.ext.automap import automap_base


def _is_many_to_many(automap_base, table):
    return None, None, None


# Monkey patch to make M2M reflect as a normal Entity class
setattr(automap, '_is_many_to_many', _is_many_to_many)
