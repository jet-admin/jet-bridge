from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from tornado import gen

from jet_bridge_base import fields
from jet_bridge_base.db import create_session
from jet_bridge_base.exceptions.sql import SqlError
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.fields.sql_params import SqlParamsSerializers
from jet_bridge_base.serializers.serializer import Serializer
from jet_bridge_base.utils.async import as_future


class SqlSerializer(Serializer):
    query = fields.CharField()
    timezone = fields.CharField(required=False)
    params = SqlParamsSerializers(required=False)

    def validate_query(self, value):
        forbidden = ['insert', 'update', 'delete', 'grant', 'show']
        for i in range(len(forbidden)):
            forbidden.append('({}'.format(forbidden[i]))
        if any(map(lambda x: ' {} '.format(value.lower()).find(' {} '.format(x)) != -1, forbidden)):
            raise ValidationError('forbidden query')

        i = 0
        while value.find('%s') != -1:
            value = value.replace('%s', ':param_{}'.format(i), 1)
            i += 1

        return value

    @gen.coroutine
    def execute(self, data):
        request = self.context.get('request')
        session = create_session(request)

        query = data['query']
        params = data.get('params', [])

        if 'timezone' in data:
            try:
                yield as_future(lambda: session.execute('SET TIME ZONE :tz', {'tz': data['timezone']}))
            except SQLAlchemyError:
                pass

        try:
            result = yield as_future(lambda: session.execute(
                text(query),
                params
            ))

            rows = list(map(lambda x: x.itervalues(), result))

            def map_column(x):
                if x == '?column?':
                    return
                return x

            return {'data': rows, 'columns': map(map_column, result.keys())}
        except (SQLAlchemyError, TypeError) as e:
            raise SqlError(e)
        finally:
            session.close()


class SqlsSerializer(Serializer):
    queries = SqlSerializer(many=True)

    def execute(self, data):
        serializer = SqlSerializer(context=self.context)

        @gen.coroutine
        def map_query(query):
            try:
                return (yield serializer.execute(query))
            except SqlError as e:
                return {'error': str(e.detail)}

        return map(map_query, data['queries'])
