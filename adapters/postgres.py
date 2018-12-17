import sqlalchemy
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from adapters.base import Adapter, registered_adapters
from models.column import Column
from models.table import Table


class PostgresAdapter(Adapter):

    def map_column(self, column):
        return Column(column.name, str(column.type))

    def map_table(self, row):
        md = sqlalchemy.MetaData()
        table = sqlalchemy.Table(row[1], md, autoload=True, autoload_with=self.engine)
        columns = table.c

        return Table(row[1], list(map(self.map_column, columns)))

    def get_tables(self):
        try:
            result = self.session.execute(
                text('SELECT * FROM pg_catalog.pg_tables WHERE schemaname = :schema'),
                {'schema': 'public'}
            )
            return list(map(lambda x: self.map_table(x), result))
        except DatabaseError:
            return []

registered_adapters['postgres'] = PostgresAdapter
