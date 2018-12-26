from jet_bridge.views.base.generic_api import GenericAPIView
from jet_bridge.views.mixins.create import CreateAPIViewMixin
from jet_bridge.views.mixins.destroy import DestroyAPIViewMixin
from jet_bridge.views.mixins.list import ListAPIViewMixin
from jet_bridge.views.mixins.retrieve import RetrieveAPIViewMixin
from jet_bridge.views.mixins.update import UpdateAPIViewMixin


class ModelAPIViewMixin(ListAPIViewMixin,
                        RetrieveAPIViewMixin,
                        DestroyAPIViewMixin,
                        CreateAPIViewMixin,
                        UpdateAPIViewMixin,
                        GenericAPIView):
    pass
