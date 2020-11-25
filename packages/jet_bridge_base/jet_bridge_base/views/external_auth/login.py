from social_core.actions import do_auth

from jet_bridge_base.configuration import configuration
from jet_bridge_base.external_auth.mixin import ExternalAuthMixin
from jet_bridge_base.views.base.api import BaseAPIView

AUTH_URI_KEY = 'auth'
PROJECT_KEY = 'project'
REDIRECT_URI_KEY = 'redirect_uri'


class ExternalAuthLoginView(ExternalAuthMixin, BaseAPIView):

    def get(self, request, *args, **kwargs):
        app = kwargs.get('app')
        return self._auth(request, app)

    def post(self, request, *args, **kwargs):
        app = kwargs.get('app')
        return self._auth(request, app)

    def _auth(self, request, app):
        auth_uri = request.get_argument('auth_uri', None)
        project = request.get_argument('project', None)
        redirect_uri = request.get_argument('redirect_uri', None)

        configuration.session_set(request, AUTH_URI_KEY, auth_uri)
        configuration.session_set(request, PROJECT_KEY, project)
        configuration.session_set(request, REDIRECT_URI_KEY, redirect_uri)

        self.init_auth(request, app)
        return do_auth(self.backend)
