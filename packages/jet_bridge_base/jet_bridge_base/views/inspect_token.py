from datetime import datetime

from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.status import HTTP_400_BAD_REQUEST
from jet_bridge_base.utils.token import parse_token, JWT_TOKEN_PREFIX, decode_jwt_token, decompress_permissions
from jet_bridge_base.views.base.api import BaseAPIView


class TokenInspectView(BaseAPIView):

    def get(self, request, *args, **kwargs):
        token_str = request.get_argument('authorization', default=None) or request.headers.get('AUTHORIZATION')
        if not token_str:
            return JSONResponse({'error': 'Token not specified'}, status=HTTP_400_BAD_REQUEST)

        token = parse_token(token_str)

        if not token:
            return JSONResponse({'error': 'Token parse failed'}, status=HTTP_400_BAD_REQUEST)

        response = {
            'token_type': token['type'],
            'token_value': token['value'],
            'token_params': token['params']
        }

        if token['type'] == JWT_TOKEN_PREFIX:
            jwt_value = decode_jwt_token(token['value'], verify_exp=False)

            response['jwt_data'] = {**jwt_value}

            if jwt_value:
                expire = datetime.utcfromtimestamp(jwt_value['exp'])

                response['jwt_data']['exp'] = expire.isoformat()
                response['jwt_data']['expired'] = datetime.utcnow() >= expire
                response['jwt_data']['exp_raw'] = jwt_value['exp']

                projects_extended = {}

                for project, user_permissions in jwt_value.get('projects', {}).items():
                    if 'permissions' in user_permissions:
                        permissions = decompress_permissions(user_permissions['permissions'])
                    else:
                        permissions = []

                    projects_extended[project] = {
                        **user_permissions,
                        'permissions': permissions,
                        'permissions_raw': user_permissions.get('permissions')
                    }

                response['jwt_data']['projects'] = projects_extended

        return JSONResponse(response)
