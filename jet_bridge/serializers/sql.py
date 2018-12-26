from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from jet_bridge import fields
from jet_bridge.db import Session
from jet_bridge.exceptions.sql import SqlError
from jet_bridge.exceptions.validation_error import ValidationError
from jet_bridge.fields.sql_params import SqlParamsSerializers
from jet_bridge.serializers.serializer import Serializer


class SqlSerializer(Serializer):
    query = fields.CharField()
    params = SqlParamsSerializers(required=False)

    class Meta:
        fields = (
            'query',
            'params',
        )

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

    def execute(self):
        session = Session()

        query = self.validated_data['query']
        params = self.validated_data.get('params', [])

        try:
            result = session.execute(
                text(query),
                params
            )

            rows = list(map(lambda x: x.itervalues(), result))

            def map_column(x):
                if x == '?column?':
                    return
                return x

            return {'data': rows, 'columns': map(map_column, result.keys())}
        except (SQLAlchemyError, TypeError) as e:
            raise SqlError(e)
