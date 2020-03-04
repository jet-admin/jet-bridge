from sqlalchemy import inspect
from sqlalchemy.orm.base import ONETOMANY

from jet_bridge_base.db import get_mapped_base
from jet_bridge_base.models import data_types
from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.serializers.model_description import ModelDescriptionSerializer
from jet_bridge_base.utils.common import merge
from jet_bridge_base.utils.db_types import map_data_type
from jet_bridge_base.views.base.api import APIView


class ModelDescriptionView(APIView):
    serializer_class = ModelDescriptionSerializer
    permission_classes = (HasProjectPermissions,)

    def get_queryset(self):
        non_editable = ['id']
        hidden = ['__jet__token']
        MappedBase = get_mapped_base(self.request)

        def map_column(column):
            params = {}

            try:
                data_type = map_data_type(column.type)
            except:
                data_type = 'NullType'

            if column.foreign_keys:
                foreign_key = next(iter(column.foreign_keys))
                data_type = data_types.FOREIGN_KEY
                params['related_model'] = {
                    'model': foreign_key.column.table.name
                }

            result = {
                'name': column.name,
                'db_column': column.name,
                'field': data_type,
                'filterable': True,
                'null': column.nullable,
                'editable': column.name not in non_editable,
                'params': params
            }

            if column.default is not None:
                result['default_type'] = 'value'
                result['default_value'] = column.default

            return result

        # def map_relation(relation):
        #     field = None
        #
        #     if relation.direction == ONETOMANY:
        #         field = 'ManyToOneRel'
        #
        #     return {
        #         'name': relation.key,
        #         'related_model': {
        #             'model': relation.table.name
        #         },
        #         'field': field,
        #         'related_model_field': relation.primaryjoin.right.name,
        #         'through': None
        #     }
        #
        # def table_relations(mapper):
        #     return list(map(map_relation, filter(lambda x: x.direction == ONETOMANY and hasattr(x, 'table'), mapper.relationships)))
        #
        # def table_m2m_relations(mapper):
        #     result = []
        #     name = mapper.selectable.name
        #
        #     for relation in mapper.relationships:
        #         if relation.direction != ONETOMANY or not hasattr(relation, 'table'):
        #             continue
        #
        #         m2m_relationships = relation.mapper.relationships.values()
        #
        #         if len(m2m_relationships) != 2:
        #             continue
        #
        #         if len(relation.table.columns) > 5:
        #             continue
        #
        #         self_relationship = m2m_relationships[1] if m2m_relationships[1].table.name == name else \
        #         m2m_relationships[0]
        #         other_relationship = m2m_relationships[0] if self_relationship == m2m_relationships[1] else \
        #         m2m_relationships[1]
        #
        #         result.append({
        #             'name': 'M2M {} {}'.format(self_relationship.table.name, other_relationship.table.name),
        #             'related_model': {
        #                 'model': other_relationship.table.name
        #             },
        #             'field': 'ManyToManyField',
        #             'related_model_field': self_relationship.table.name,
        #             'through': {'model': relation.table.name}
        #         })
        #
        #     return result

        def map_table(cls):
            mapper = inspect(cls)
            name = mapper.selectable.name

            from jet_bridge_base.configuration import configuration
            additional = configuration.get_model_description(name)

            result = {
                'model': name,
                'db_table': name,
                'fields': list(map(map_column, mapper.columns)),
                'hidden': name in hidden or name in configuration.get_hidden_model_description(),
                # 'relations': table_relations(mapper) + table_m2m_relations(mapper),
                'primary_key_field': mapper.primary_key[0].name
            }

            if additional:
                result = merge(result, additional)

            return result

        return list(map(map_table, MappedBase.classes))

    def get(self, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.serializer_class(instance=queryset, many=True)
        return JSONResponse(serializer.representation_data)
