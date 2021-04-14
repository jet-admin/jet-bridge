from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from jet_bridge_base import fields
from jet_bridge_base.db import create_session
from jet_bridge_base.exceptions.sql import SqlError
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.fields.sql_params import SqlParamsSerializers
from jet_bridge_base.serializers.serializer import Serializer


class SqlSerializer(Serializer):
    query = fields.CharField()
    timezone = fields.CharField(required=False)
    params = SqlParamsSerializers(required=False)
    params_obj = fields.JSONField(required=False)
    v = fields.IntegerField(default=1)

    def validate(self, attrs):
        forbidden = ['insert', 'update', 'delete', 'grant', 'show']
        for i in range(len(forbidden)):
            forbidden.append('({}'.format(forbidden[i]))
        if any(map(lambda x: ' {} '.format(attrs['query'].lower()).find(' {} '.format(x)) != -1, forbidden)):
            raise ValidationError({'query': 'forbidden query'})

        if attrs['v'] < 2:
            i = 0
            while attrs['query'].find('%s') != -1:
                attrs['query'] = attrs['query'].replace('%s', ':param_{}'.format(i), 1)
                i += 1

        return attrs

    def execute(self, data):
        request = self.context.get('request')
        session = create_session(request)

        query = data['query']

        if data['v'] >= 2:
            params = data.get('params_obj', {})
        else:
            params = data.get('params', [])

        if 'timezone' in data:
            try:
                session.execute('SET TIME ZONE :tz', {'tz': data['timezone']})
            except SQLAlchemyError:
                session.rollback()
                pass

        try:
            result = session.execute(
                text(query),
                params
            )

            def map_column(x):
                if x == '?column?':
                    return
                return x

            def map_row_column(x):
                if isinstance(x, bytes):
                    try:
                        return x.decode('utf-8')
                    except UnicodeDecodeError:
                        return x.hex()
                else:
                    return x

            def map_row(row):
                return list(map(lambda x: map_row_column(row[x]), row.keys()))

            return {'data': list(map(map_row, result)), 'columns': list(map(map_column, result.keys()))}
        except SQLAlchemyError as e:
            session.rollback()
            raise SqlError(e)
        except TypeError as e:
            raise SqlError(e)
        except Exception as e:
            raise SqlError(e)
        finally:
            session.close()


class SqlsSerializer(Serializer):
    queries = SqlSerializer(many=True)

    def execute(self, data):
        serializer = SqlSerializer(context=self.context)

        def map_query(query):
            try:
                return serializer.execute(query)
            except SqlError as e:
                return {'error': str(e.detail)}

        return list(map(map_query, data['queries']))
