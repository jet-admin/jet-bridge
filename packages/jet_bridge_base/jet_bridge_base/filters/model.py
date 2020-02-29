from jet_bridge_base.filters.filter_class import FilterClass
from jet_bridge_base.filters.model_m2m import get_model_m2m_filter
from jet_bridge_base.filters.model_relation import get_model_relation_filter
from jet_bridge_base.filters.model_search import get_model_search_filter
from jet_bridge_base.filters.model_segment import get_model_segment_filter
from jet_bridge_base.filters.order_by import OrderFilter


def get_model_filter_class(request, Model):
    search_filter = get_model_search_filter(Model)
    model_m2m_filter = get_model_m2m_filter(Model)
    model_segment_filter = get_model_segment_filter(request, Model)
    model_relation_filter = get_model_relation_filter(request, Model)

    class ModelFilterClass(FilterClass):
        _order_by = OrderFilter()
        _search = search_filter()
        _m2m = model_m2m_filter()
        _segment = model_segment_filter()
        _relation = model_relation_filter()

        class Meta:
            model = Model

    return ModelFilterClass
