from six.moves.urllib_parse import quote

from jet_bridge import settings
from jet_bridge.responses.base import Response
from jet_bridge.utils.backend import register_token, is_token_activated
from jet_bridge.views.base.api import APIView


class RegisterHandler(APIView):

    def get(self, *args, **kwargs):
        token, created = register_token()

        if not token:
            return

        if is_token_activated():
            response = Response({
                'message': 'Project token is already activated'
            })
            self.write_response(response)
            return

        if settings.WEB_BASE_URL.startswith('https') and not self.request.full_url().startswith('https'):
            web_base_url = 'http{}'.format(settings.WEB_BASE_URL[5:])
        else:
            web_base_url = settings.WEB_BASE_URL

        url = '{}/projects/register/{}'.format(web_base_url, token.token)
        query_string = 'referrer={}'.format(quote(self.request.full_url().encode('utf8')))

        self.redirect('%s?%s' % (url, query_string))
