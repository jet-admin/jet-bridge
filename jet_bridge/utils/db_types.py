from jet_bridge.models import data_types

map_data_types = [
    {'query': 'VARCHAR', 'operator': 'startswith', 'date_type': data_types.TEXT},
    {'query': 'TEXT', 'operator': 'equals', 'date_type': data_types.TEXT},
    {'query': 'BOOLEAN', 'operator': 'equals', 'date_type': data_types.BOOLEAN},
    {'query': 'INTEGER', 'operator': 'equals', 'date_type': data_types.INTEGER},
    {'query': 'SMALLINT', 'operator': 'equals', 'date_type': data_types.INTEGER},
    {'query': 'NUMERIC', 'operator': 'startswith', 'date_type': data_types.FLOAT},
    {'query': 'VARCHAR', 'operator': 'startswith', 'date_type': data_types.DATE_TIME},
    {'query': 'TIMESTAMP', 'operator': 'startswith', 'date_type': data_types.TIMESTAMP},
]
default_data_type = data_types.TEXT


def map_data_type(value):
    for rule in map_data_types:
        if rule['operator'] == 'equals' and value == rule['query']:
            return rule['date_type']
        elif rule['operator'] == 'startswith' and value[:len(rule['query'])] == rule['query']:
            return rule['date_type']
    return default_data_type
