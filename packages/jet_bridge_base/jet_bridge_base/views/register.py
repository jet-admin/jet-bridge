from six.moves.urllib_parse import quote

from jet_bridge_base import settings
from jet_bridge_base.responses.base import Response
from jet_bridge_base.responses.redirect import RedirectResponse
from jet_bridge_base.status import HTTP_400_BAD_REQUEST
from jet_bridge_base.views.base.api import APIView


class RegisterView(APIView):

    def get(self, *args, **kwargs):
        if not settings.PROJECT:
            return Response('Project name is not set', status=HTTP_400_BAD_REQUEST)

        if not settings.TOKEN:
            return Response('Project token is not set', status=HTTP_400_BAD_REQUEST)

        token = self.request.get_argument('token', '')
        install_type = self.request.get_argument('install_type', '')

        if settings.WEB_BASE_URL.startswith('https') and not self.request.full_url().startswith('https'):
            web_base_url = 'http{}'.format(settings.WEB_BASE_URL[5:])
        else:
            web_base_url = settings.WEB_BASE_URL

        if token:
            url = '{}/projects/register/{}'.format(web_base_url, token)
        else:
            url = '{}/projects/register'.format(web_base_url)

        parameters = [
            ['project', settings.PROJECT],
            ['referrer', self.request.full_url().encode('utf8')],
        ]

        if install_type:
            parameters.append(['install_type', install_type])

        query_string = '&'.join(map(lambda x: '{}={}'.format(x[0], quote(x[1])), parameters))

        return RedirectResponse('%s?%s' % (url, query_string))
