import json

from six import string_types

from jet_bridge_base.db_types import inspect_uniform
from jet_bridge_base.filters.char_filter import CharFilter
from jet_bridge_base.filters.filter import EMPTY_VALUES


def get_model_semantic_search(Model):
    mapper = inspect_uniform(Model)

    class SemanticSearchFilter(CharFilter):
        def filter(self, qs, value):
            if value in EMPTY_VALUES:
                return qs

            if isinstance(value, string_types):
                try:
                    params = json.loads(value)
                except ValueError:
                    return qs
            else:
                params = value

            field_name = params['field']
            embedding = params['embedding']
            similarity_gte = params.get('similarity_gte')

            column = mapper.columns[field_name]
            expr = column.cosine_distance(embedding)

            if similarity_gte is not None:
                qs = qs.where((1 - expr) >= similarity_gte)

            return qs.order_by(None).order_by(expr)

    return SemanticSearchFilter
