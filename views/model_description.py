from adapters.base import registered_adapters
from db import Session, engine
from responses.base import Response
from serializers.model_description import ModelDescriptionSerializer
from views.base.api import APIView


class ModelDescriptionsHandler(APIView):
    serializer_class = ModelDescriptionSerializer
    session = Session()

    def get_queryset(self):
        Adapter = registered_adapters.get('postgres')

        if not Adapter:
            return []

        adapter = Adapter(engine, self.session)
        hidden = ['__jet__token']

        def map_column(column):
            return {
                'name': column.name,
                'db_column': column.name,
                'field': column.data_type,
                'filterable': True,
                'editable': True
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
