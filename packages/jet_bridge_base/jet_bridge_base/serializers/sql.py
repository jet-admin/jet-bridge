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

    def validate_query(self, value):
        # TODO allow any sql operations, maybe other serializer class for non select?
        # forbidden = ['insert', 'update', 'delete', 'grant', 'show']
        # for i in range(len(forbidden)):
        #     forbidden.append('({}'.format(forbidden[i]))
        # if any(map(lambda x: ' {} '.format(value.lower()).find(' {} '.format(x)) != -1, forbidden)):
        #     raise ValidationError('forbidden query')

        i = 0
        while value.find('%s') != -1:
            value = value.replace('%s', ':param_{}'.format(i), 1)
            i += 1

        return value

    def execute(self, data):
        request = self.context.get('request')
        session = create_session(request)

        query = data['query']
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

            if not result.returns_rows:
                return {'data': [], 'columns': []}

            rows = result.fetchall()

            def map_row_column(x):
                if isinstance(x, bytes):
                    try:
                        return x.decode('utf-8')
                    except UnicodeDecodeError:
                        return x.hex()
                else:
                    return x

            def map_row(x):
                return list(map(map_row_column, x))

            return {'data': list(map(map_row, rows)), 'columns': list(result.keys())}
        except SQLAlchemyError as e:
            session.rollback()
            raise SqlError(e)
        except TypeError as e:
            raise SqlError(e)
        finally:
            session.commit()
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
