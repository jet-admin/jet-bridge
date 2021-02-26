from jet_bridge_base.models import data_types
from jet_bridge_base.logger import logger

from sqlalchemy.sql import sqltypes

map_data_types = [
    {'query': sqltypes.VARCHAR, 'date_type': data_types.TEXT},
    {'query': sqltypes.Unicode, 'date_type': data_types.TEXT},
    {'query': sqltypes.TEXT, 'date_type': data_types.TEXT},
    {'query': sqltypes.BOOLEAN, 'date_type': data_types.BOOLEAN},
    {'query': sqltypes.INTEGER, 'date_type': data_types.INTEGER},
    {'query': sqltypes.SMALLINT, 'date_type': data_types.INTEGER},
    {'query': sqltypes.BIGINT, 'date_type': data_types.INTEGER},
    {'query': sqltypes.NUMERIC, 'date_type': data_types.FLOAT},
    {'query': sqltypes.DATE, 'date_type': data_types.DATE_TIME},
    {'query': sqltypes.DATETIME, 'date_type': data_types.DATE_TIME},
    {'query': sqltypes.TIMESTAMP, 'date_type': data_types.DATE_TIME},
    {'query': sqltypes.JSON, 'date_type': data_types.JSON},
]
default_data_type = data_types.TEXT

try:
    from geoalchemy2 import types
    map_data_types.append({'query': types.Geometry, 'date_type': data_types.GEOMETRY})
    map_data_types.append({'query': types.Geography, 'date_type': data_types.GEOGRAPHY})
except ImportError:
    pass

try:
    from sqlalchemy.dialects import mssql
    map_data_types.append({'query': mssql.BIT, 'date_type': data_types.BOOLEAN})
    map_data_types.append({'query': mssql.VARBINARY, 'date_type': data_types.TEXT})
    map_data_types.append({'query': mssql.SMALLDATETIME, 'date_type': data_types.DATE_TIME})
except ImportError:
    pass


def map_data_type(value):
    for rule in reversed(map_data_types):
        if isinstance(value, rule['query']):
            return rule['date_type']
    logger.warning('Unknown database type: {}'.format(str(value)))
    return default_data_type
