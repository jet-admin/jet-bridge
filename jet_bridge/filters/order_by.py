from sqlalchemy import sql, desc

from jet_bridge.filters.char_filter import CharFilter
from jet_bridge.filters.filter import EMPTY_VALUES


class OrderFilter(CharFilter):

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        if len(value) < 2:
            return qs.filter(sql.false())

        descending = value[0:1] == '-'
        value = value[1:] if descending else value
        entity = qs._primary_entity.entity_zero_or_selectable.entity
        column = getattr(entity, value, None)

        if column is None:
            return qs.filter(sql.false())

        if descending:
            column = desc(column)

        return qs.order_by(column)
