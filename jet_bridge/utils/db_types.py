from jet_bridge.models import data_types

from sqlalchemy.sql import sqltypes

map_data_types = [
    {'query': sqltypes.VARCHAR, 'operator': 'startswith', 'date_type': data_types.TEXT},
    {'query': sqltypes.TEXT, 'operator': 'equals', 'date_type': data_types.TEXT},
    {'query': sqltypes.BOOLEAN, 'operator': 'equals', 'date_type': data_types.BOOLEAN},
    {'query': sqltypes.INTEGER, 'operator': 'equals', 'date_type': data_types.INTEGER},
    {'query': sqltypes.SMALLINT, 'operator': 'equals', 'date_type': data_types.INTEGER},
    {'query': sqltypes.NUMERIC, 'operator': 'startswith', 'date_type': data_types.FLOAT},
    {'query': sqltypes.DATETIME, 'operator': 'startswith', 'date_type': data_types.DATE_TIME},
    {'query': sqltypes.TIMESTAMP, 'operator': 'startswith', 'date_type': data_types.DATE_TIME},
]
default_data_type = data_types.TEXT


def map_data_type(value):
    for rule in map_data_types:
        if isinstance(value, rule['query']):
            return rule['date_type']
    return default_data_type
