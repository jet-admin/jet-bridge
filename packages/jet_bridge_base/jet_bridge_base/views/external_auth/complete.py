import json

from social_core.actions import do_complete

from jet_bridge_base import settings
from jet_bridge_base.configuration import configuration
from jet_bridge_base.external_auth.mixin import ExternalAuthMixin
from jet_bridge_base.responses.template import TemplateResponse
from jet_bridge_base.views.base.api import BaseAPIView
from jet_bridge_base.views.external_auth.login import REDIRECT_URI_KEY, AUTH_URI_KEY, PROJECT_KEY


class ExternalAuthCompleteView(ExternalAuthMixin, BaseAPIView):

    def get(self, request, *args, **kwargs):
        backend = kwargs.get('app')
        return self._complete(request, backend)

    def post(self, request, *args, **kwargs):
        backend = kwargs.get('app')
        return self._complete(request, backend)

    def _complete(self, request, app):
        self.init_auth(request, app)

        # Hack for passing SSO
        setattr(self.backend, 'sso', app)
        result = do_complete(
            self.backend,
            login=lambda: None
        )

        success = result and result.get('auth')
        auth_uri = configuration.session_get(request, AUTH_URI_KEY, '/api/')
        project = configuration.session_get(request, PROJECT_KEY)
        redirect_uri = configuration.session_get(request, REDIRECT_URI_KEY)

        data = {
            'sso': app,
            'token': settings.TOKEN,
            'project': project,
            'redirect_uri': redirect_uri
        }

        if success:
            data['result'] = True
            data['username'] = result['details'].get('username')
            data['email'] = result['details'].get('email')
            data['first_name'] = result['details'].get('first_name')
            data['last_name'] = result['details'].get('last_name')
            data['full_name'] = result['details'].get('fullname')
        else:
            data['result'] = False
            data['error'] = 'Authentication failed'

        return TemplateResponse('external_auth_complete.html', status=200, data={
            'context': json.dumps({
                'url': auth_uri,
                'data': data
            })
        })
