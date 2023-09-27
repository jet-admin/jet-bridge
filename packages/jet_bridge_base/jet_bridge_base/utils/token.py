import json
import jwt
from jwt import PyJWTError

from jet_bridge_base import settings
from jet_bridge_base.utils.compress import decompress_data

USER_TOKEN_PREFIX = 'Token'
PROJECT_TOKEN_PREFIX = 'ProjectToken'
JWT_TOKEN_PREFIX = 'JWT'
BEARER_TOKEN_PREFIX = 'Bearer'


def parse_token(value):
    tokens = value.split(',') if value else []
    result = {}

    for token in tokens:
        try:
            type, data = token.split(' ', 2)
            items = data.split(';')

            if len(items) == 0:
                continue

            try:
                params = dict(map(lambda x: x.split('=', 2), items[1:]))
            except ValueError:
                params = {}

            result[type] = {
                'type': type,
                'value': items[0],
                'params': params
            }
        except (ValueError, AttributeError):
            pass

    if JWT_TOKEN_PREFIX in result:
        return result[JWT_TOKEN_PREFIX]
    elif len(result):
        return list(result.values())[0]


def decode_jwt_token(token, verify_exp=True):
    JWT_VERIFY_KEY = '\n'.join([line.lstrip() for line in settings.JWT_VERIFY_KEY.split('\\n')])

    try:
        return jwt.decode(token, key=JWT_VERIFY_KEY, algorithms=['RS256'], options={'verify_exp': verify_exp})
    except PyJWTError:
        return None


def decompress_permissions(permissions):
    decoded = decompress_data(permissions)
    return json.loads(decoded)
