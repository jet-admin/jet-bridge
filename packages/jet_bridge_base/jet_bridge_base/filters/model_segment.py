from jet_bridge_base.db_types import empty_filter, inspect_uniform
from jet_bridge_base.filters.char_filter import CharFilter
from jet_bridge_base.filters.filter import EMPTY_VALUES
from jet_bridge_base.serializers.sql import SqlSerializer


def get_model_segment_filter(request, Model):
    mapper = inspect_uniform(Model)
    primary_key = mapper.primary_key[0].name

    class ModelSegmentFilter(CharFilter):
        def filter(self, qs, value):
            value = self.clean_value(value)
            if value in EMPTY_VALUES:
                return qs

            body = self.handler.data

            if not isinstance(body, dict):
                return qs.filter(empty_filter(Model))

            items = list(filter(lambda x: x.get('name') == value, body.get('segments', [])))

            if len(items) == 0:
                return qs.filter(empty_filter(Model))

            query = items[0].get('query')

            serializer = SqlSerializer(data={'query': query}, context={'request': request})
            serializer.is_valid(raise_exception=True)
            result = serializer.execute()
            columns = list(result['columns'])
            rows = result['data']

            if len(columns) == 0 or len(rows) == 0:
                return qs.filter(empty_filter(Model))

            ids = list(map(lambda x: list(x)[0], rows))

            return qs.filter(getattr(Model, primary_key).in_(ids))

    return ModelSegmentFilter
