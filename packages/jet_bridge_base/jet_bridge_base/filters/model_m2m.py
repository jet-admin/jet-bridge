from jet_bridge_base.db_types import empty_filter, inspect_uniform
from jet_bridge_base.filters.char_filter import CharFilter
from jet_bridge_base.filters.filter import EMPTY_VALUES


def get_model_m2m_filter(Model):
    mapper = inspect_uniform(Model)

    class ModelM2MFilter(CharFilter):

        def filter(self, qs, value):
            if value in EMPTY_VALUES:
                return qs

            params = value.split(',', 2)

            if len(params) < 2:
                return qs.filter(empty_filter(Model))

            relation_name, value = params

            relations = []

            for relationship in mapper.relationships:
                for sub_relationship in relationship.mapper.relationships:
                    if sub_relationship.table.name != relation_name:
                        continue

                    relations.append({
                        'relationship': relationship,
                        'sub_relationship': sub_relationship
                    })

            if len(relations) == 0:
                return qs.filter(empty_filter(Model))

            relation = relations[0]
            relationship_entity = relation['relationship'].mapper.entity
            id_column_name = relation['sub_relationship'].primaryjoin.right.name
            relationship_entity_id_key = getattr(relationship_entity, id_column_name)

            qs = qs.join(relationship_entity)
            qs = qs.filter(relationship_entity_id_key == value)

            return qs

    return ModelM2MFilter
