from sqlalchemy import sql, desc

from jet_bridge.filters.char_filter import CharFilter
from jet_bridge.filters.filter import EMPTY_VALUES


class OrderFilter(CharFilter):

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        if len(value) < 2:
            return qs.filter(sql.false())

        ordering = value.split(',')

        def map_field(name):
            descending = False
            if name.startswith('-'):
                name = name[1:]
                descending = True
            field = getattr(self.model, name)
            if descending:
                field = desc(field)
            return field

        if len(ordering):
            qs = qs.order_by(*map(lambda x: map_field(x), ordering))

        return qs
