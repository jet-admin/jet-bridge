from jet_bridge_base import settings
from jet_bridge_base.configuration import configuration
from jet_bridge_base.exceptions.not_found import NotFound
from jet_bridge_base.external_auth.utils import load_strategy, load_backends_classes


class ExternalAuthMixin(object):
    strategy = None
    backends = {}
    backend = None

    def __init__(self, *args, **kwargs):
        self.init_backends()
        super(ExternalAuthMixin, self).__init__(*args, **kwargs)

    def init_backends(self):
        backend_paths = list(map(lambda x: x.get('backend_path'), settings.SSO_APPLICATIONS.values()))
        self.backends = load_backends_classes(backend_paths)

    def init_auth(self, app):
        redirect_uri = self.redirect_uri(app)

        try:
            name = configuration.clean_sso_application_name(app)
            config = settings.SSO_APPLICATIONS[name]
        except KeyError:
            raise NotFound

        backend_path = config.get('backend_path')
        Backend = self.backends.get(backend_path)

        self.strategy = load_strategy(self, config)
        self.backend = Backend(self.strategy, redirect_uri)

    def redirect_uri(self, app):
        return '/api/external_auth/complete/{0}/'.format(app)
