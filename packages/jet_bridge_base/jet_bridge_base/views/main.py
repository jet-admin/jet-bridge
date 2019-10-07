from jet_bridge_base.responses.redirect import RedirectResponse
from jet_bridge_base.views.base.api import APIView


class MainView(APIView):

    def get(self):
        return RedirectResponse('/api/')
