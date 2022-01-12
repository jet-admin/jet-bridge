from jet_bridge_base.models import data_types
from jet_bridge_base.logger import logger

from sqlalchemy.sql import sqltypes

map_data_types = [
    {'sql_type': sqltypes.VARCHAR, 'map_type': data_types.CHAR, 'db_type': data_types.CHAR},
    {'sql_type': sqltypes.CHAR, 'map_type': data_types.CHAR, 'db_type': data_types.FIXED_CHAR},
    {'sql_type': sqltypes.Unicode, 'map_type': data_types.CHAR, 'db_type': data_types.CHAR},
    {'sql_type': sqltypes.TEXT, 'map_type': data_types.TEXT, 'db_type': data_types.TEXT},
    {'sql_type': sqltypes.BOOLEAN, 'map_type': data_types.BOOLEAN, 'db_type': data_types.BOOLEAN},
    {'sql_type': sqltypes.INTEGER, 'map_type': data_types.INTEGER, 'db_type': data_types.INTEGER},
    {'sql_type': sqltypes.SMALLINT, 'map_type': data_types.INTEGER, 'db_type': data_types.SMALL_INTEGER},
    {'sql_type': sqltypes.BIGINT, 'map_type': data_types.INTEGER, 'db_type': data_types.BIG_INTEGER},
    {'sql_type': sqltypes.NUMERIC, 'map_type': data_types.FLOAT, 'db_type': data_types.NUMBER},
    {'sql_type': sqltypes.FLOAT, 'map_type': data_types.FLOAT, 'db_type': data_types.FLOAT},
    {'sql_type': sqltypes.DECIMAL, 'map_type': data_types.FLOAT, 'db_type': data_types.DECIMAL},
    {'sql_type': sqltypes.DATE, 'map_type': data_types.DATE, 'db_type': data_types.DATE},
    {'sql_type': sqltypes.DATETIME, 'map_type': data_types.DATE_TIME, 'db_type': data_types.DATE_TIME},
    {'sql_type': sqltypes.TIMESTAMP, 'map_type': data_types.DATE_TIME, 'db_type': data_types.TIMESTAMP},
    {'sql_type': sqltypes.JSON, 'map_type': data_types.JSON, 'db_type': data_types.JSON},
]
default_sql_type = sqltypes.VARCHAR
default_map_type = data_types.CHAR
default_db_type = data_types.CHAR

try:
    from geoalchemy2 import types
    map_data_types.append({'sql_type': types.Geometry, 'map_type': data_types.GEOMETRY, 'db_type': data_types.GEOMETRY})
    map_data_types.append({'sql_type': types.Geography, 'map_type': data_types.GEOGRAPHY, 'db_type': data_types.GEOGRAPHY})
except ImportError:
    pass

try:
    from sqlalchemy.dialects import postgresql
    map_data_types.append({'sql_type': postgresql.DOUBLE_PRECISION, 'map_type': data_types.FLOAT, 'db_type': data_types.DOUBLE_PRECISION})
except ImportError:
    pass
try:
    from sqlalchemy.dialects import mssql
    map_data_types.append({'sql_type': mssql.BIT, 'map_type': data_types.BOOLEAN, 'db_type': data_types.BOOLEAN})
    map_data_types.append({'sql_type': mssql.VARBINARY, 'map_type': data_types.CHAR, 'db_type': data_types.CHAR})
    map_data_types.append({'sql_type': mssql.SMALLDATETIME, 'map_type': data_types.DATE_TIME, 'db_type': data_types.DATE_TIME})
except ImportError:
    pass


def sql_to_map_type(value):
    for rule in reversed(map_data_types):
        if isinstance(value, rule['sql_type']) or issubclass(value, rule['sql_type']):
            return rule['map_type']
    logger.warning('Unknown database type: {}'.format(str(value)))
    return default_map_type


def map_to_sql_type(value):
    for rule in map_data_types:
        if rule['map_type'] == value:
            return rule['sql_type']
    logger.warning('Unknown database type: {}'.format(str(value)))
    return default_sql_type


def sql_to_db_type(value):
    for rule in reversed(map_data_types):
        if isinstance(value, rule['sql_type']):
            return rule['db_type']
    logger.warning('Unknown database type: {}'.format(str(value)))
    return default_db_type


def db_to_sql_type(value):
    for rule in map_data_types:
        if rule['db_type'] == value:
            return rule['sql_type']
    logger.warning('Unknown database type: {}'.format(str(value)))
    return default_sql_type
