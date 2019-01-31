from sqlalchemy import inspect
from sqlalchemy.orm.base import ONETOMANY
from sqlalchemy.util import ImmutableProperties

from jet_bridge.db import Session, MappedBase
from jet_bridge.models import data_types
from jet_bridge.permissions import HasProjectPermissions
from jet_bridge.responses.base import Response
from jet_bridge.serializers.model_description import ModelDescriptionSerializer
from jet_bridge.utils.db_types import map_data_type
from jet_bridge.views.base.api import APIView


class ModelDescriptionsHandler(APIView):
    serializer_class = ModelDescriptionSerializer
    permission_classes = (HasProjectPermissions,)
    session = Session()

    def get_queryset(self):
        non_editable = ['id']
        hidden = ['__jet__token']

        def map_column(column):
            params = {}
            data_type = map_data_type(column.type)

            if len(column.foreign_keys):
                foreign_key = next(iter(column.foreign_keys))
                data_type = data_types.FOREIGN_KEY
                params['related_model'] = {
                    'model': foreign_key.column.table.name
                }

            return {
                'name': column.name,
                'db_column': column.name,
                'field': data_type,
                'filterable': True,
                'editable': column.name not in non_editable,
                'params': params
            }

        def map_relation(relation):
            field = None

            if relation.direction == ONETOMANY:
                field = 'ManyToOneRel'

            return {
                'name': relation.key,
                'related_model': {
                    'model': relation.table.name
                },
                'field': field,
                'related_model_field': relation.primaryjoin.right.name,
                'through': None
            }

        def table_relations(mapper):
            return list(map(map_relation, filter(lambda x: x.direction == ONETOMANY, mapper.relationships)))

        def table_m2m_relations(mapper):
            result = []
            name = mapper.selectable.name

            for relation in mapper.relationships:
                if relation.direction != ONETOMANY:
                    continue

                m2m_relationships = relation.mapper.relationships.values()

                if len(m2m_relationships) != 2:
                    continue

                if len(relation.table.columns) > 5:
                    continue

                self_relationship = m2m_relationships[1] if m2m_relationships[1].table.name == name else \
                m2m_relationships[0]
                other_relationship = m2m_relationships[0] if self_relationship == m2m_relationships[1] else \
                m2m_relationships[1]

                result.append({
                    'name': 'M2M {} {}'.format(self_relationship.table.name, other_relationship.table.name),
                    'related_model': {
                        'model': other_relationship.table.name
                    },
                    'field': 'ManyToManyField',
                    'related_model_field': self_relationship.table.name,
                    'through': {'model': relation.table.name}
                })

            return result

        def map_table(cls):
            mapper = inspect(cls)
            name = mapper.selectable.name

            return {
                'model': name,
                'db_table': name,
                'fields': list(map(map_column, mapper.columns)),
                'hidden': name in hidden,
                'relations': table_relations(mapper) + table_m2m_relations(mapper),
                'primary_key_field': mapper.primary_key[0].name
            }

        return list(map(map_table, MappedBase.classes))

    def get(self, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.serializer_class(instance=queryset, many=True)
        response = Response(serializer.representation_data)
        self.write_response(response)
