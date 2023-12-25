import six
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from jet_bridge_base import fields
from jet_bridge_base.serializers.serializer import Serializer
from jet_bridge_base.utils.exceptions import validation_error_from_database_error
from jet_bridge_base.utils.queryset import get_session_engine

data_types = [
    {'query': 'VARCHAR', 'operator': 'startswith', 'data_type': fields.CharField},
    {'query': 'TEXT', 'operator': 'equals', 'data_type': fields.CharField},
    {'query': 'BIT', 'operator': 'equals', 'data_type': fields.BooleanField},
    {'query': 'BOOLEAN', 'operator': 'equals', 'data_type': fields.BooleanField},
    {'query': 'INTEGER[]', 'operator': 'startswith', 'data_type': fields.ArrayField},
    {'query': 'INTEGER', 'operator': 'equals', 'data_type': fields.IntegerField},
    {'query': 'SMALLINT', 'operator': 'equals', 'data_type': fields.IntegerField},
    {'query': 'BIGINT', 'operator': 'equals', 'data_type': fields.IntegerField},
    {'query': 'FLOAT', 'operator': 'equals', 'data_type': fields.FloatField},
    {'query': 'DECIMAL', 'operator': 'equals', 'data_type': fields.FloatField},
    {'query': 'DOUBLE_PRECISION', 'operator': 'equals', 'data_type': fields.FloatField},
    {'query': 'MONEY', 'operator': 'equals', 'data_type': fields.FloatField},
    {'query': 'SMALLMONEY', 'operator': 'equals', 'data_type': fields.FloatField},
    {'query': 'NUMERIC', 'operator': 'startswith', 'data_type': fields.CharField},
    {'query': 'VARCHAR', 'operator': 'startswith', 'data_type': fields.CharField},
    {'query': 'TIMESTAMP', 'operator': 'startswith', 'data_type': fields.DateTimeField},
    {'query': 'DATETIME', 'operator': 'startswith', 'data_type': fields.DateTimeField},
    {'query': 'JSON', 'operator': 'startswith', 'data_type': fields.JSONField},
    {'query': 'ARRAY', 'operator': 'equals', 'data_type': fields.JSONField},
    {'query': 'geometry', 'operator': 'startswith', 'data_type': fields.WKTField},
    {'query': 'geography', 'operator': 'startswith', 'data_type': fields.WKTField},
]
default_data_type = fields.CharField


def get_column_data_type(column):
    try:
        data_type = six.text_type(column.type)
    except:
        data_type = 'NullType'

    for rule in data_types:
        if rule['operator'] == 'equals' and data_type == rule['query']:
            return rule['data_type']
        elif rule['operator'] == 'startswith' and data_type[:len(rule['query'])] == rule['query']:
            return rule['data_type']

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
                data_type = get_column_data_type(column)
                kwargs = {}

                # if column.primary_key and column.autoincrement:
                #     kwargs['read_only'] = True
                if column.autoincrement or column.default or column.server_default or column.nullable:
                    kwargs['required'] = False

                field = data_type(**kwargs)
                field.field_name = field_name
                result.append(field)

        return result

    def create_instance(self, validated_data):
        ModelClass = self.meta.model
        return ModelClass(**validated_data)

    def create(self, validated_data):
        mapper = inspect(self.meta.model)
        primary_key = mapper.primary_key[0]
        primary_key_specified = primary_key.name in validated_data

        if primary_key.autoincrement and primary_key_specified and not validated_data.get(primary_key.name):
            primary_key_specified = False
            del validated_data[primary_key.name]

        instance = self.create_instance(validated_data)
        self.session.add(instance)

        if primary_key.autoincrement and primary_key_specified:
            if get_session_engine(self.session) == 'postgresql':
                self.session.execute('''
                    SELECT 
                        pg_catalog.setval(
                            pg_catalog.pg_get_serial_sequence('"{}"."{}"', '{}'), 
                            max("{}")
                        ) 
                    FROM 
                        "{}"."{}"
                '''.format(
                    mapper.selectable.schema,
                    mapper.selectable.name,
                    primary_key.name,
                    primary_key.name,
                    mapper.selectable.schema,
                    mapper.selectable.name,
                ))

        try:
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise validation_error_from_database_error(e, self.model)

        return instance

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        try:
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise validation_error_from_database_error(e, self.model)

        return instance
