from jet_bridge.views.base.api import APIView


class MainHandler(APIView):

    def get(self):
        self.redirect('/api/')
