from jet_bridge_base.db_types import inspect_uniform
from jet_bridge_base.filters import lookups
from jet_bridge_base.filters.filter import Filter
from jet_bridge_base.filters.filter_for_dbfield import filter_for_column


class FilterClass(object):
    filters = []

    def __init__(self, *args, **kwargs):
        self.meta = getattr(self, 'Meta', None)
        if 'context' in kwargs:
            self.handler = kwargs['context'].get('handler', None)
        self.update_filters()

    def update_filters(self):
        filters = []

        if self.meta:
            if hasattr(self.meta, 'model'):
                Model = self.meta.model
                mapper = inspect_uniform(Model)
                columns = mapper.columns

                if hasattr(self.meta, 'fields'):
                    columns = filter(lambda x: x.name in self.meta.fields, columns)

                for column in columns:
                    item = filter_for_column(column)
                    for lookup in item['lookups']:
                        for exclude in [False, True]:
                            instance = item['filter_class'](
                                name=column.key,
                                column=column,
                                lookup=lookup,
                                exclude=exclude
                            )
                            filters.append(instance)

        declared_filters = filter(lambda x: isinstance(x[1], Filter), map(lambda x: (x, getattr(self, x)), dir(self)))

        for filter_name, filter_item in declared_filters:
            filter_item.name = filter_name
            filter_item.model = Model
            filter_item.handler = self.handler
            filters.append(filter_item)

        self.filters = filters

    def filter_queryset(self, request, queryset):
        def get_filter_value(name, filters_instance=None):
            return request.get_argument_safe(name, None)

        for item in self.filters:
            if item.name:
                argument_name = '{}__{}'.format(item.name, item.lookup)
                if item.exclude:
                    argument_name = 'exclude__{}'.format(argument_name)
                value = get_filter_value(argument_name, item)

                if value is None and item.lookup == lookups.DEFAULT_LOOKUP:
                    argument_name = item.name
                    if item.exclude:
                        argument_name = 'exclude__{}'.format(argument_name)
                    value = get_filter_value(argument_name, item)
            else:
                value = None

            queryset = item.filter(queryset, value)
        return queryset
