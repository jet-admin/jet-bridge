import sqlalchemy
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from adapters.base import Adapter, registered_adapters
from models.column import Column
from models import data_types
from models.table import Table


class PostgresAdapter(Adapter):
    data_types = [
        {'query': 'VARCHAR', 'operator': 'startswith', 'date_type': data_types.TEXT},
        {'query': 'TEXT', 'operator': 'equals', 'date_type': data_types.TEXT},
        {'query': 'BOOLEAN', 'operator': 'equals', 'date_type': data_types.BOOLEAN},
        {'query': 'INTEGER', 'operator': 'equals', 'date_type': data_types.INTEGER},
        {'query': 'SMALLINT', 'operator': 'equals', 'date_type': data_types.INTEGER},
        {'query': 'NUMERIC', 'operator': 'startswith', 'date_type': data_types.FLOAT},
        {'query': 'VARCHAR', 'operator': 'startswith', 'date_type': data_types.DATE_TIME},
        {'query': 'TIMESTAMP', 'operator': 'startswith', 'date_type': data_types.TIMESTAMP},
    ]

    def map_column(self, column):
        return Column(column.name, self.map_data_type(str(column.type)))

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
