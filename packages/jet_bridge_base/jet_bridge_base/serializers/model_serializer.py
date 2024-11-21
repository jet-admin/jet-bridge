import datetime
import six
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import sqltypes

from jet_bridge_base import fields
from jet_bridge_base.db import get_default_timezone
from jet_bridge_base.db_types import inspect_uniform, MongoColumn, get_session_engine
from jet_bridge_base.serializers.serializer import Serializer
from jet_bridge_base.utils.exceptions import validation_error_from_database_error
from jet_bridge_base.models import data_types

data_types = [
    {'query': 'VARCHAR', 'operator': 'startswith', 'map_type': data_types.CHAR, 'data_type': fields.CharField},
    {'query': 'TEXT', 'operator': 'equals', 'map_type': data_types.TEXT, 'data_type': fields.CharField},
    {'query': 'BIT', 'operator': 'equals', 'map_type': data_types.BOOLEAN, 'data_type': fields.BooleanField},
    {'query': 'TINYINT', 'operator': 'equals', 'map_type': data_types.SMALL_INTEGER, 'data_type': fields.IntegerField},
    {'query': 'BOOLEAN', 'operator': 'equals', 'map_type': data_types.BOOLEAN, 'data_type': fields.BooleanField},
    {'query': 'INTEGER[]', 'operator': 'startswith', 'map_type': data_types.JSON, 'data_type': fields.ArrayField},
    {'query': 'INTEGER', 'operator': 'equals', 'map_type': data_types.INTEGER, 'data_type': fields.IntegerField},
    {'query': 'SMALLINT', 'operator': 'equals', 'map_type': data_types.SMALL_INTEGER, 'data_type': fields.IntegerField},
    {'query': 'BIGINT', 'operator': 'equals', 'map_type': data_types.BIG_INTEGER, 'data_type': fields.IntegerField},
    {'query': 'FLOAT', 'operator': 'equals', 'map_type': data_types.FLOAT, 'data_type': fields.FloatField},
    {'query': 'DECIMAL', 'operator': 'equals', 'map_type': data_types.DECIMAL, 'data_type': fields.FloatField},
    {'query': 'DOUBLE_PRECISION', 'operator': 'equals', 'map_type': data_types.DOUBLE_PRECISION, 'data_type': fields.FloatField},
    {'query': 'MONEY', 'operator': 'equals', 'map_type': data_types.MONEY, 'data_type': fields.FloatField},
    {'query': 'SMALLMONEY', 'operator': 'equals', 'map_type': data_types.MONEY, 'data_type': fields.FloatField},
    {'query': 'NUMERIC', 'operator': 'startswith', 'map_type': data_types.NUMBER, 'data_type': fields.CharField},
    {'query': 'VARCHAR', 'operator': 'startswith', 'map_type': data_types.CHAR, 'data_type': fields.CharField},
    {'query': 'TIMESTAMP', 'operator': 'startswith', 'map_type': data_types.DATE_TIME, 'data_type': fields.DateTimeField},
    {'query': 'DATETIME', 'operator': 'startswith', 'map_type': data_types.DATE_TIME, 'data_type': fields.DateTimeField},
    {'query': 'JSON', 'operator': 'startswith', 'map_type': data_types.JSON, 'data_type': fields.JSONField},
    {'query': 'ARRAY', 'operator': 'equals', 'map_type': data_types.JSON, 'data_type': fields.JSONField},
    {'query': 'BINARY', 'operator': 'startswith', 'map_type': data_types.BINARY, 'data_type': fields.BinaryField},
    {'query': 'VARBINARY', 'operator': 'startswith', 'map_type': data_types.BINARY, 'data_type': fields.BinaryField},
    {'query': 'geometry', 'operator': 'startswith', 'map_type': data_types.GEOMETRY, 'data_type': fields.WKTField},
    {'query': 'geography', 'operator': 'startswith', 'map_type': data_types.GEOGRAPHY, 'data_type': fields.WKTField},
]
default_data_type = fields.CharField


def get_column_data_type(column):
    if isinstance(column, MongoColumn):
        for rule in reversed(data_types):
            if rule['map_type'] == column.type:
                return rule['data_type']
    else:
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
            mapper = inspect_uniform(self.meta.model)
            columns = dict(map(lambda x: (x.key, x), mapper.columns))

            for field_name in self.meta.model_fields:
                column = columns.get(field_name)
                data_type = get_column_data_type(column)
                kwargs = {'context': self.context, 'serializer': self}

                # if column.primary_key and column.autoincrement:
                #     kwargs['read_only'] = True
                if column.autoincrement or column.default or column.server_default or column.nullable:
                    kwargs['required'] = False

                field = data_type(**kwargs)
                field.field_name = field_name
                result.append(field)

        return result

    def prepare_datetime_timezone_naive(self, column, value, default_timezone):
        if not isinstance(value, datetime.datetime) or not value.tzinfo:
            return value

        if not default_timezone:
            return value

        column_type = column.expression.type

        if isinstance(column_type, sqltypes.DATETIME) and not column_type.timezone:
            return value.astimezone(default_timezone)
        else:
            return value

    def prepare_data_timezone_naive(self, data):
        request = self.context.get('request')
        default_timezone = get_default_timezone(request) if request else None

        for key, value in data.items():
            column = getattr(self.model, key, None)

            if not column:
                continue

            data[key] = self.prepare_datetime_timezone_naive(column, value, default_timezone)

    def create_instance(self, validated_data):
        ModelClass = self.meta.model
        return ModelClass(**validated_data)

    def create(self, validated_data):
        mapper = inspect_uniform(self.meta.model)
        primary_key = mapper.primary_key[0]
        primary_key_specified = primary_key.name in validated_data

        if primary_key.autoincrement and primary_key_specified and not validated_data.get(primary_key.name):
            primary_key_specified = False
            del validated_data[primary_key.name]

        self.prepare_data_timezone_naive(validated_data)

        instance = self.create_instance(validated_data)
        self.session.add(instance)

        if primary_key.autoincrement and primary_key_specified:
            if get_session_engine(self.session) == 'postgresql':
                if mapper.selectable.schema:
                    table_name = '"{}"."{}"'.format(mapper.selectable.schema, mapper.selectable.name)
                else:
                    table_name = '"{}"'.format(mapper.selectable.name)

                self.session.execute('''
                    SELECT 
                        pg_catalog.setval(
                            pg_catalog.pg_get_serial_sequence('{}', '{}'), 
                            max("{}")
                        ) 
                    FROM 
                        {}
                '''.format(
                    table_name,
                    primary_key.name,
                    primary_key.name,
                    table_name,
                ))

        try:
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise validation_error_from_database_error(e, self.model)

        return instance

    def update(self, instance, validated_data):
        self.prepare_data_timezone_naive(validated_data)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        try:
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise validation_error_from_database_error(e, self.model)

        return instance
