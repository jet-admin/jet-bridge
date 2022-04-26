from jet_bridge_base.utils.queryset import get_session_engine
from sqlalchemy import inspect

from jet_bridge_base.filters import lookups
from jet_bridge_base.filters.filter import Filter
from jet_bridge_base.filters.filter_for_dbfield import filter_for_data_type


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
                mapper = inspect(Model)
                columns = mapper.columns

                if hasattr(self.meta, 'fields'):
                    columns = filter(lambda x: x.name in self.meta.fields, columns)

                for column in columns:
                    item = filter_for_data_type(column.type)
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
        session = request.session

        def get_filter_value(name, filters_instance=None):
            value = request.get_argument_safe(name, None)

            if filters_instance and value is not None and get_session_engine(session) == 'bigquery':
                python_type = filters_instance.column.type.python_type
                value = python_type(value)

            return value

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
