import sqlalchemy
from sqlalchemy import inspect, or_, cast

from jet_bridge_base.filters.char_filter import CharFilter
from jet_bridge_base.filters.filter import EMPTY_VALUES


def search_queryset(qs, mapper, search):
    if search in EMPTY_VALUES:
        return qs

    def map_column(column):
        if isinstance(column.type, (sqlalchemy.Integer, sqlalchemy.Numeric)):
            return cast(column, sqlalchemy.String).__eq__(search)
        elif isinstance(column.type, (sqlalchemy.JSON, sqlalchemy.Enum)):
            return cast(column, sqlalchemy.String).ilike('%{}%'.format(search))
        elif isinstance(column.type, sqlalchemy.String):
            return column.ilike('%{}%'.format(search))

    operators = list(filter(lambda x: x is not None, map(map_column, mapper.columns)))

    return qs.filter(or_(*operators))


def get_model_search_filter(Model):
    mapper = inspect(Model)

    class ModelSearchFilter(CharFilter):
        def filter(self, qs, value):
            value = self.clean_value(value)
            return search_queryset(qs, mapper, value)

    return ModelSearchFilter
