import sqlalchemy
from jet_bridge.filters.filter import EMPTY_VALUES
from sqlalchemy import inspect

from jet_bridge.db import MappedBase
from jet_bridge.filters.char_filter import CharFilter


def filter_search_field(field):
    allowed_fields = [
        sqlalchemy.String,
        sqlalchemy.JSON,
    ]

    return isinstance(field.type, tuple(allowed_fields))


def get_model_relation_filter(Model):
    mapper = inspect(Model)

    class ModelSearchFilter(CharFilter):
        def filter(self, qs, value):
            if value in EMPTY_VALUES:
                return qs

            current_table = mapper.tables[0]
            path = list(map(lambda x: x.split('.'), value.split('|')))
            path_len = len(path)

            for i in range(path_len):
                item = path[i]
                last = i == path_len - 1

                if not last:
                    current_table_column = current_table.columns[item[0]]

                    related_table = MappedBase.metadata.tables[item[1]]
                    related_table_column = related_table.columns[item[2]]

                    qs = qs.join(related_table, current_table_column == related_table_column)
                    current_table = related_table
                else:
                    current_table_column = current_table.columns[item[0]]
                    value = item[1].split(',')
                    qs = qs.filter(current_table_column.in_(value))

            return qs

    return ModelSearchFilter
