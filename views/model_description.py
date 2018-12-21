from adapters.base import registered_adapters
from db import Session, engine
from serializers.model_description import ModelDescriptionSerializer
from views.base.api import APIView
from views.mixins.list import ListAPIViewMixin


class ModelDescriptionsHandler(ListAPIViewMixin, APIView):
    serializer_class = ModelDescriptionSerializer
    pagination_class = None

    def get_queryset(self):
        session = Session()
        Adapter = registered_adapters.get('postgres')

        if not Adapter:
            return []

        adapter = Adapter(engine, session)

        def map_column(column):
            return {
                'name': column.name,
                'db_column': column.name,
                'field': column.data_type,
            }

        def map_table(table):
            return {
                'model': table.name,
                'db_table': table.name,
                'fields': list(map(map_column, table.columns)),
                'hidden': False
            }

        return list(map(map_table, adapter.get_tables()))
