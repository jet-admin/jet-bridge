from jet_bridge_base.db_types import desc_uniform, empty_filter
from jet_bridge_base.filters.char_filter import CharFilter
from jet_bridge_base.filters.filter import EMPTY_VALUES


class OrderFilter(CharFilter):

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        if len(value) < 2:
            return qs.filter(empty_filter(self.model))

        ordering = value.split(',')

        def map_field(name):
            descending = False
            if name.startswith('-'):
                name = name[1:]
                descending = True
            field = getattr(self.model, name)
            if descending:
                field = desc_uniform(field)
            return field

        if ordering:
            qs = qs.order_by(*map(lambda x: map_field(x), ordering))

        return qs
