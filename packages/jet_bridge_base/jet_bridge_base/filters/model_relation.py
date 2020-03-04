import sqlalchemy
from jet_bridge_base.filters.filter import EMPTY_VALUES
from sqlalchemy import inspect

from jet_bridge_base.db import get_mapped_base
from jet_bridge_base.filters.char_filter import CharFilter


def filter_search_field(field):
    allowed_fields = [
        sqlalchemy.String,
        sqlalchemy.JSON,
    ]

    return isinstance(field.type, tuple(allowed_fields))


def get_model_relation_filter(request, Model):
    mapper = inspect(Model)
    MappedBase = get_mapped_base(request)

    class ModelRelationFilter(CharFilter):
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

    return ModelRelationFilter
