from sqlalchemy import inspect

import fields
from serializers.serializer import Serializer


data_types = [
    {'query': 'VARCHAR', 'operator': 'startswith', 'date_type': fields.CharField},
    {'query': 'TEXT', 'operator': 'equals', 'date_type': fields.CharField},
    {'query': 'BOOLEAN', 'operator': 'equals', 'date_type': fields.BooleanField},
    {'query': 'INTEGER', 'operator': 'equals', 'date_type': fields.CharField},
    {'query': 'SMALLINT', 'operator': 'equals', 'date_type': fields.CharField},
    {'query': 'NUMERIC', 'operator': 'startswith', 'date_type': fields.CharField},
    {'query': 'VARCHAR', 'operator': 'startswith', 'date_type': fields.CharField},
    {'query': 'TIMESTAMP', 'operator': 'startswith', 'date_type': fields.CharField},
]
default_data_type = fields.CharField


def map_data_type(value):
    for rule in data_types:
        if rule['operator'] == 'equals' and value == rule['query']:
            return rule['date_type']
        elif rule['operator'] == 'startswith' and value[:len(rule['query'])] == rule['query']:
            return rule['date_type']
    return default_data_type


def map_column(column):
    date_type = map_data_type(str(column.type))
    return (column.key, date_type())


def get_model_serializer(Model):
    mapper = inspect(Model)

    class ModelSerializer(Serializer):
        class Meta:
            dynamic_fields = dict(map(map_column, mapper.columns))

    return ModelSerializer
