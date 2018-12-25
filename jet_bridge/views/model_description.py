from jet_bridge.adapters.base import registered_adapters
from jet_bridge.db import Session, engine
from jet_bridge.responses.base import Response
from jet_bridge.serializers.model_description import ModelDescriptionSerializer
from jet_bridge.views.base.api import APIView


class ModelDescriptionsHandler(APIView):
    serializer_class = ModelDescriptionSerializer
    session = Session()

    def get_queryset(self):
        Adapter = registered_adapters.get('postgres')

        if not Adapter:
            return []

        adapter = Adapter(engine, self.session)
        non_editable = ['id']
        hidden = ['__jet__token']

        def map_column(column):
            return {
                'name': column.name,
                'db_column': column.name,
                'field': column.data_type,
                'filterable': True,
                'editable': column.name not in non_editable
            }

        def map_table(table):
            return {
                'model': table.name,
                'db_table': table.name,
                'fields': list(map(map_column, table.columns)),
                'hidden': table.name in hidden
            }

        return list(map(map_table, adapter.get_tables()))

    def get(self, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.serializer_class(instance=queryset, many=True)
        response = Response(serializer.representation_data)
        self.write_response(response)
