from jet_bridge_base.models import data_types
from jet_bridge_base.logger import logger
from jet_bridge_base.utils.classes import issubclass_safe, is_instance_or_subclass

from sqlalchemy.sql import sqltypes

map_data_types = [
    {'sql_type': sqltypes.VARCHAR, 'map_type': data_types.CHAR, 'db_type': data_types.CHAR},
    {'sql_type': sqltypes.CHAR, 'map_type': data_types.CHAR, 'db_type': data_types.FIXED_CHAR},
    {'sql_type': sqltypes.Unicode, 'map_type': data_types.CHAR, 'db_type': data_types.CHAR},
    {'sql_type': sqltypes.Text, 'map_type': data_types.TEXT, 'db_type': data_types.TEXT},
    {'sql_type': sqltypes.Enum, 'map_type': data_types.SELECT, 'db_type': data_types.SELECT},
    {'sql_type': sqltypes.Boolean, 'map_type': data_types.BOOLEAN, 'db_type': data_types.BOOLEAN, 'convert': lambda x: '{}::boolean'.format(x)},
    {'sql_type': sqltypes.Integer, 'map_type': data_types.INTEGER, 'db_type': data_types.INTEGER, 'convert': lambda x: '{}::integer'.format(x)},
    {'sql_type': sqltypes.SmallInteger, 'map_type': data_types.INTEGER, 'db_type': data_types.SMALL_INTEGER, 'convert': lambda x: '{}::integer'.format(x)},
    {'sql_type': sqltypes.BigInteger, 'map_type': data_types.INTEGER, 'db_type': data_types.BIG_INTEGER, 'convert': lambda x: '{}::bigint'.format(x)},
    {'sql_type': sqltypes.Numeric, 'map_type': data_types.FLOAT, 'db_type': data_types.NUMBER, 'convert': lambda x: '{}::numeric'.format(x)},
    {'sql_type': sqltypes.Float, 'map_type': data_types.FLOAT, 'db_type': data_types.FLOAT, 'convert': lambda x: '{}::double precision'.format(x)},
    {'sql_type': sqltypes.DECIMAL, 'map_type': data_types.FLOAT, 'db_type': data_types.DECIMAL, 'convert': lambda x: '{}::double precision'.format(x)},
    {'sql_type': sqltypes.Date, 'map_type': data_types.DATE, 'db_type': data_types.DATE, 'convert': lambda x: '{}::text::date'.format(x)},
    {'sql_type': sqltypes.DateTime, 'map_type': data_types.DATE_TIME, 'db_type': data_types.DATE_TIME, 'convert': lambda x: '{}::timestamp with time zone'.format(x)},
    {'sql_type': sqltypes.TIMESTAMP, 'map_type': data_types.DATE_TIME, 'db_type': data_types.TIMESTAMP, 'convert': lambda x: '{}::timestamp with time zone'.format(x)},
    {'sql_type': sqltypes.JSON, 'map_type': data_types.JSON, 'db_type': data_types.JSON, 'convert': lambda x: '{}::json'.format(x)},
    {'sql_type': sqltypes.ARRAY, 'map_type': data_types.JSON, 'db_type': data_types.JSON, 'convert': lambda x: '{}::json'.format(x)},
    {'sql_type': sqltypes.BINARY, 'map_type': data_types.BINARY, 'db_type': data_types.BINARY},
    {'sql_type': sqltypes.VARBINARY, 'map_type': data_types.BINARY, 'db_type': data_types.BINARY},
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
    map_data_types.append({'sql_type': postgresql.UUID, 'map_type': data_types.UUID, 'db_type': data_types.UUID})
    map_data_types.append({'sql_type': postgresql.DOUBLE_PRECISION, 'map_type': data_types.FLOAT, 'db_type': data_types.DOUBLE_PRECISION, 'convert': lambda x: '{}::double precision'.format(x)})
except ImportError:
    pass

try:
    from sqlalchemy.dialects import mysql
    map_data_types.append({'sql_type': mysql.TINYINT, 'map_type': data_types.BOOLEAN, 'db_type': data_types.BOOLEAN})
except ImportError:
    pass

try:
    from sqlalchemy.dialects import mssql
    map_data_types.append({'sql_type': mssql.BIT, 'map_type': data_types.BOOLEAN, 'db_type': data_types.BOOLEAN})
    map_data_types.append({'sql_type': mssql.VARBINARY, 'map_type': data_types.CHAR, 'db_type': data_types.CHAR})
    map_data_types.append({'sql_type': mssql.SMALLDATETIME, 'map_type': data_types.DATE_TIME, 'db_type': data_types.DATE_TIME})
    map_data_types.append({'sql_type': mssql.MONEY, 'map_type': data_types.FLOAT, 'db_type': data_types.MONEY, 'convert': lambda x: '{}::double precision'.format(x)})
    map_data_types.append({'sql_type': mssql.SMALLMONEY, 'map_type': data_types.FLOAT, 'db_type': data_types.MONEY, 'convert': lambda x: '{}::double precision'.format(x)})
except ImportError:
    pass


def sql_to_map_type(value):
    for rule in reversed(map_data_types):
        if is_instance_or_subclass(value, rule['sql_type']):
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
        if is_instance_or_subclass(value, rule['sql_type']):
            return rule['db_type']
    logger.warning('Unknown database type: {}'.format(str(value)))
    return default_db_type


def db_to_sql_type(value):
    for rule in map_data_types:
        if rule['db_type'] == value:
            return rule['sql_type']
    logger.warning('Unknown database type: {}'.format(str(value)))
    return default_sql_type


def get_db_type_convert(value):
    for rule in map_data_types:
        if rule['db_type'] == value:
            return rule.get('convert')
    logger.warning('Unknown database type: {}'.format(str(value)))


def get_sql_type_convert(value):
    for rule in reversed(map_data_types):
        if is_instance_or_subclass(value, rule['sql_type']):
            return rule.get('convert')
    logger.warning('Unknown database type: {}'.format(str(value)))
