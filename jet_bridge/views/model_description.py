from sqlalchemy import inspect

from jet_bridge.db import Session, MappedBase
from jet_bridge.responses.base import Response
from jet_bridge.serializers.model_description import ModelDescriptionSerializer
from jet_bridge.utils.db_types import map_data_type
from jet_bridge.views.base.api import APIView


class ModelDescriptionsHandler(APIView):
    serializer_class = ModelDescriptionSerializer
    session = Session()

    def get_queryset(self):
        non_editable = ['id']
        hidden = ['__jet__token']

        def map_column(column):
            return {
                'name': column.name,
                'db_column': column.name,
                'field': map_data_type(str(column.type)),
                'filterable': True,
                'editable': column.name not in non_editable
            }

        def map_table(cls):
            mapper = inspect(cls)
            name = mapper.selectable.name
            return {
                'model': name,
                'db_table': name,
                'fields': list(map(map_column, mapper.columns)),
                'hidden': name in hidden
            }

        return list(map(map_table, MappedBase.classes))

    def get(self, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.serializer_class(instance=queryset, many=True)
        response = Response(serializer.representation_data)
        self.write_response(response)
