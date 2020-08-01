from social_core.utils import build_absolute_uri
from social_core.strategy import BaseStrategy

from jet_bridge_base.configuration import configuration
from jet_bridge_base.responses.redirect import RedirectResponse
from jet_bridge_base.utils.common import merge_two_dicts


class JetBridgeStrategy(BaseStrategy):

    def __init__(self, storage, request_handler, config, tpl=None):
        self.request_handler = request_handler
        self.request = request_handler.request
        self.config = config
        super(JetBridgeStrategy, self).__init__(storage, tpl)

    def authenticate(self, *args, **kwargs):
        result = super(JetBridgeStrategy, self).authenticate(*args, **kwargs)
        # Ignore redirect response by returning user of another class
        return {
            'auth': True,
            'details': result.details,
            'extra_data': result.extra_data
        } if result else {}

    def get_setting(self, name):
        settings = merge_two_dicts(self.config, {
            'pipeline': [
                'social_core.pipeline.social_auth.social_details',
                'jet_bridge_base.external_auth.pipeline.save_extra_data',
                'jet_bridge_base.external_auth.pipeline.return_result'
            ]
        })
        key = name.lower()
        return settings[key]

    def request_data(self, merge=True):
        return merge_two_dicts(self.request.data, self.request.query_arguments)

    def request_host(self):
        return self.request.host

    def redirect(self, url):
        return RedirectResponse(url)

    def html(self, content):
        self.request_handler.write(content)

    def session_get(self, name, default=None):
        value = configuration.session_get(self.request, name, default)
        if value:
            return value
        return default

    def session_set(self, name, value):
        configuration.session_set(self.request, name, value)

    def session_pop(self, name):
        value = self.session_get(name)
        configuration.session_clear(self.request, name)
        return value

    def session_setdefault(self, name, value):
        pass

    def build_absolute_uri(self, path=None):
        return build_absolute_uri(
            '{0}://{1}'.format(self.request.protocol, self.request.host),
            path
        )
