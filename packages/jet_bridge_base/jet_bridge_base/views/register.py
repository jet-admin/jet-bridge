from six.moves.urllib_parse import quote

from jet_bridge_base import settings
from jet_bridge_base.responses.base import Response
from jet_bridge_base.responses.redirect import RedirectResponse
from jet_bridge_base.status import HTTP_400_BAD_REQUEST
from jet_bridge_base.views.base.api import BaseAPIView


class RegisterView(BaseAPIView):

    def get(self, request, *args, **kwargs):
        if not settings.PROJECT:
            return Response('Project name is not set', status=HTTP_400_BAD_REQUEST)

        if not settings.TOKEN:
            return Response('Project token is not set', status=HTTP_400_BAD_REQUEST)

        token = request.get_argument('token', '')
        environment_type = settings.ENVIRONMENT_TYPE

        if settings.WEB_BASE_URL.startswith('https') and not request.full_url().startswith('https'):
            web_base_url = 'http{}'.format(settings.WEB_BASE_URL[5:])
        else:
            web_base_url = settings.WEB_BASE_URL

        url = '{}/builder/{}/resources/database/create/'.format(web_base_url, settings.PROJECT)

        parameters = [
            ['engine', settings.DATABASE_ENGINE],
            ['referrer', request.full_url().encode('utf8')],
        ]

        if token:
            parameters.append(['token', token])

        if environment_type:
            parameters.append(['environment_type', environment_type])

        query_string = '&'.join(map(lambda x: '{}={}'.format(x[0], quote(x[1])), parameters))

        return RedirectResponse('%s#%s' % (url, query_string))
