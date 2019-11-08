import six
from sqlalchemy import inspect

from jet_bridge_base import fields
from jet_bridge_base.serializers.serializer import Serializer
from jet_bridge_base.utils.exceptions import validation_error_from_database_error

data_types = [
    {'query': 'VARCHAR', 'operator': 'startswith', 'date_type': fields.CharField},
    {'query': 'TEXT', 'operator': 'equals', 'date_type': fields.CharField},
    {'query': 'BOOLEAN', 'operator': 'equals', 'date_type': fields.BooleanField},
    {'query': 'INTEGER[]', 'operator': 'startswith', 'date_type': fields.ArrayField},
    {'query': 'INTEGER', 'operator': 'equals', 'date_type': fields.IntegerField},
    {'query': 'SMALLINT', 'operator': 'equals', 'date_type': fields.IntegerField},
    {'query': 'NUMERIC', 'operator': 'startswith', 'date_type': fields.CharField},
    {'query': 'VARCHAR', 'operator': 'startswith', 'date_type': fields.CharField},
    {'query': 'TIMESTAMP', 'operator': 'startswith', 'date_type': fields.DateTimeField},
    {'query': 'DATETIME', 'operator': 'startswith', 'date_type': fields.DateTimeField},
    {'query': 'JSON', 'operator': 'startswith', 'date_type': fields.JSONField},
    {'query': 'geometry', 'operator': 'startswith', 'date_type': fields.WKTField},
    {'query': 'geography', 'operator': 'startswith', 'date_type': fields.WKTField},
]
default_data_type = fields.CharField


def get_column_data_type(column):
    try:
        data_type = six.text_type(column.type)
    except:
        data_type = 'NullType'

    for rule in data_types:
        if rule['operator'] == 'equals' and data_type == rule['query']:
            return rule['date_type']
        elif rule['operator'] == 'startswith' and data_type[:len(rule['query'])] == rule['query']:
            return rule['date_type']

    return default_data_type


class ModelSerializer(Serializer):

    def __init__(self, *args, **kwargs):
        super(ModelSerializer, self).__init__(*args, **kwargs)
        self.session = kwargs.get('context', {}).get('session', None)
        self.model = self.meta.model

    def get_fields(self):
        result = super(ModelSerializer, self).get_fields()

        if hasattr(self.meta, 'model_fields'):
            mapper = inspect(self.meta.model)
            columns = dict(map(lambda x: (x.key, x), mapper.columns))

            for field_name in self.meta.model_fields:
                column = columns.get(field_name)
                date_type = get_column_data_type(column)
                kwargs = {}

                if column.primary_key and column.autoincrement:
                    kwargs['read_only'] = True

                field = date_type(**kwargs)
                field.field_name = field_name
                result.append(field)

        return result

    def create_instance(self, validated_data):
        ModelClass = self.meta.model
        return ModelClass(**validated_data)

    def create(self, validated_data):
        instance = self.create_instance(validated_data)
        self.session.add(instance)

        try:
            self.session.commit()
        except Exception as e:
            raise validation_error_from_database_error(e, self.model)

        return instance

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        try:
            self.session.commit()
        except Exception as e:
            raise validation_error_from_database_error(e, self.model)

        return instance
