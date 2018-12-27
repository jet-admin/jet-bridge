import sqlalchemy
from sqlalchemy import inspect, or_, sql

from jet_bridge.filters.char_filter import CharFilter
from jet_bridge.filters.filter import EMPTY_VALUES
from jet_bridge.filters.filter_class import FilterClass


def filter_search_field(field):
    allowed_fields = [
        sqlalchemy.String,
        sqlalchemy.JSON,
    ]

    return isinstance(field.type, tuple(allowed_fields))


def get_model_search_filter(Model):
    mapper = inspect(Model)
    search_fields = list(map(lambda x: x, filter(filter_search_field, mapper.columns)))

    class SearchFilter(CharFilter):
        def filter(self, qs, value):
            value = self.clean_value(value)
            if value in EMPTY_VALUES:
                return qs

            operators = list(map(lambda x: x.ilike('%{}%'.format(value)), search_fields))
            return qs.filter(or_(*operators))

    return SearchFilter


def get_model_m2m_filter(Model):
    mapper = inspect(Model)

    class M2MFilter(CharFilter):

        def filter(self, qs, value):
            if value in EMPTY_VALUES:
                return qs

            params = value.split(',', 2)

            if len(params) < 2:
                return qs.filter(sql.false())

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
                return qs.filter(sql.false())

            relation = relations[0]
            relationship_entity = relation['relationship'].mapper.entity
            id_column_name = relation['sub_relationship'].primaryjoin.right.name
            relationship_entity_id_key = getattr(relationship_entity, id_column_name)

            qs = qs.join(relationship_entity)
            qs = qs.filter(relationship_entity_id_key == value)

            return qs

    return M2MFilter


def get_model_filter_class(Model):
    search_filter = get_model_search_filter(Model)
    model_m2m_filter = get_model_m2m_filter(Model)

    class ModelFilterClass(FilterClass):
        _search = search_filter()
        _m2m = model_m2m_filter()

        class Meta:
            model = Model

    return ModelFilterClass
