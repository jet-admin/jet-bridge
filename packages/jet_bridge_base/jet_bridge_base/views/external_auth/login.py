from social_core.actions import do_auth

from jet_bridge_base.configuration import configuration
from jet_bridge_base.external_auth.mixin import ExternalAuthMixin
from jet_bridge_base.views.base.api import BaseAPIView

AUTH_URI_KEY = 'auth'
PROJECT_KEY = 'project'
REDIRECT_URI_KEY = 'redirect_uri'


class ExternalAuthLoginView(ExternalAuthMixin, BaseAPIView):

    def get(self, *args, **kwargs):
        app = kwargs.get('app')
        return self._auth(app)

    def post(self, *args, **kwargs):
        app = kwargs.get('app')
        return self._auth(app)

    def _auth(self, app):
        auth_uri = self.request.get_argument('auth_uri', None)
        project = self.request.get_argument('project', None)
        redirect_uri = self.request.get_argument('redirect_uri', None)

        configuration.session_set(self.request, AUTH_URI_KEY, auth_uri)
        configuration.session_set(self.request, PROJECT_KEY, project)
        configuration.session_set(self.request, REDIRECT_URI_KEY, redirect_uri)

        self.init_auth(app)
        return do_auth(self.backend)
