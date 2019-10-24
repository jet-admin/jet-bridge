from six.moves.urllib_parse import quote

from jet_bridge_base import settings
from jet_bridge_base.responses.redirect import RedirectResponse
from jet_bridge_base.views.base.api import APIView


class RegisterView(APIView):

    def get(self, *args, **kwargs):
        token = self.request.get_argument('token', '')

        if settings.WEB_BASE_URL.startswith('https') and not self.request.full_url().startswith('https'):
            web_base_url = 'http{}'.format(settings.WEB_BASE_URL[5:])
        else:
            web_base_url = settings.WEB_BASE_URL

        if token:
            url = '{}/projects/register/{}'.format(web_base_url, token)
        else:
            url = '{}/projects/register'.format(web_base_url)

        query_string = 'referrer={}'.format(quote(self.request.full_url().encode('utf8')))

        return RedirectResponse('%s?%s' % (url, query_string))
