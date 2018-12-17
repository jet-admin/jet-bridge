import json

import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError, DatabaseError
from sqlalchemy.orm import sessionmaker

from serializers.model_description import ModelDescriptionSerializer
from views import APIView, ListAPIViewMixin

engine = create_engine('postgresql://postgres:password@localhost:5432/jetty')
Session = sessionmaker(bind=engine)


class ModelDescriptionsHandler(ListAPIViewMixin, APIView):
    serializer_class = ModelDescriptionSerializer

    def get_queryset(self):
        session = Session()

        # try:
        # result = session.execute('select * from table where id=:id', {'id': 7})
        result = session.execute(text('SELECT * FROM pg_catalog.pg_tables WHERE schemaname = :schema'), {'schema': 'public'})
        # except DatabaseError:
        #     pass

        # print(result.keys())

        def serialize_row(row):
            md = sqlalchemy.MetaData()
            table = sqlalchemy.Table(row[1], md, autoload=True, autoload_with=engine)
            columns = table.c

            return {
                # 'app_label': 'admin',
                'db_table': row[1],
                'model': row[1],
                'fields': list(map(lambda c: {
                    'db_column': c.name,
                    # 'editable': False,
                    'field': str(c.type),
                    # 'filterable': True,
                    # 'is_relation': False,
                    'name': c.name,
                    # 'params': {related_model: null}
                    # 'verbose_name': 'action time',
                }, columns)),
                # 'flex_fields': [],
                'hidden': False,
                'relations': [],
                # 'actions': [],
                # 'verbose_name': 'log entry',
                # 'verbose_name_plural': 'log entries'
            }

        return list(map(lambda x: serialize_row(x), result))
