import base64
import gzip
import json

import jwt
from jwt import PyJWTError

from jet_bridge_base import settings
from jet_bridge_base.utils.backend import project_auth
from jet_bridge_base.utils.crypt import get_sha256_hash


def decompress_data(value):
    try:
        bytes = base64.b64decode(value)
        data = gzip.decompress(bytes)
        return data.decode('utf-8')
    except AttributeError:
        return value.decode('zlib')


def compress_data(data):
    try:
        encoded = data.encode('utf-8')
        bytes = gzip.compress(encoded)
        return str(base64.b64encode(bytes), 'utf-8')
    except AttributeError:
        return data.encode('zlib')


class BasePermission(object):

    def has_permission(self, view, request):
        return True

    def has_object_permission(self, view, request, obj):
        return True


class HasProjectPermissions(BasePermission):
    user_token_prefix = 'Token'
    project_token_prefix = 'ProjectToken'
    jwt_token_prefix = 'JWT'
    bearer_token_prefix = 'Bearer'

    def parse_token(self, value):
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

        if self.jwt_token_prefix in result:
            return result[self.jwt_token_prefix]
        elif len(result):
            return list(result.values())[0]

    def has_view_permissions(self, view_permissions, user_permissions, project_token):
        if not view_permissions:
            return True
        elif user_permissions.get('owner'):
            return True
        elif user_permissions.get('super_group'):
            return True

        if 'permissions' in user_permissions:
            decoded = decompress_data(user_permissions['permissions'])
            permissions = json.loads(decoded)
        else:
            permissions = []

        view_permission_type = view_permissions.get('permission_type', '')
        view_permission_object = view_permissions.get('permission_object', '')
        view_permission_actions = view_permissions.get('permission_actions', '')

        if user_permissions.get('read_only'):
            if view_permission_type == 'model' and all(map(lambda x: x in ['r'], list(view_permission_actions))):
                return True
            elif view_permission_type == 'project' and view_permission_object in ['project_settings']:
                return True
            else:
                return False

        token_hash = get_sha256_hash(project_token.replace('-', '').lower())

        for item in permissions:
            item_type = item.get('permission_type', '')
            item_object = item.get('permission_object', '')
            item_actions = item.get('permission_actions', '')

            if view_permission_type == 'model':
                resource_token_hash = item.get('resource_token_hash', '')
                item_object_model = item_object.split('.', 1)[-1:][0]

                if resource_token_hash and resource_token_hash != token_hash:
                    continue

                if item_type != view_permission_type or item_object_model != view_permission_object:
                    continue
            else:
                if item_type != view_permission_type or item_object != view_permission_object:
                    continue

            return view_permission_actions in item_actions

        return False

    def has_permission(self, view, request):
        # return True
        token = self.parse_token(request.headers.get('AUTHORIZATION'))
        view_permissions = view.required_project_permission(request) if hasattr(view, 'required_project_permission') else None

        if not token:
            return False

        bridge_settings = request.get_bridge_settings()

        if bridge_settings:
            project_token = bridge_settings.get('token')
            project = bridge_settings.get('project')
        else:
            project_token = settings.TOKEN
            project = settings.PROJECT

        if token['type'] == self.jwt_token_prefix:
            JWT_VERIFY_KEY = '\n'.join([line.lstrip() for line in settings.JWT_VERIFY_KEY.split('\\n')])

            try:
                result = jwt.decode(token['value'], key=JWT_VERIFY_KEY, algorithms=['RS256'])
            except PyJWTError:
                return False

            user_permissions = result.get('projects', {}).get(project)

            if user_permissions is None:
                return False

            request.project = result.get('project')
            request.environment = result.get('environment')
            request.resource_token = project_token

            return self.has_view_permissions(view_permissions, user_permissions, project_token)
        elif token['type'] == self.user_token_prefix:
            result = project_auth(token['value'], project_token, view_permissions, token['params'])

            # if result.get('warning'):
            #     view.headers['X-Application-Warning'] = result['warning']

            return result['result']
        elif token['type'] == self.project_token_prefix:
            result = project_auth(token['value'], project_token, view_permissions, token['params'])

            # if result.get('warning'):
            #     view.headers['X-Application-Warning'] = result['warning']

            return result['result']
        elif token['type'] == self.bearer_token_prefix:
            return settings.BEARER_AUTH_KEY and token['value'] == settings.BEARER_AUTH_KEY
        else:
            return False


class ReadOnly(BasePermission):

    def has_permission(self, view, request):
        if not settings.READ_ONLY:
            return True
        if request.action in ['create', 'update', 'partial_update', 'destroy']:
            return False
        return True


class AdministratorPermissions(BasePermission):
    def has_permission(self, view, request):
        key = request.get_argument('key', None)

        if not key:
            return False

        if settings.BEARER_AUTH_KEY and key == settings.BEARER_AUTH_KEY:
            return True
        else:
            JWT_VERIFY_KEY = '\n'.join([line.lstrip() for line in settings.JWT_VERIFY_KEY.split('\\n')])

            try:
                result = jwt.decode(key, key=JWT_VERIFY_KEY, algorithms=['RS256'])
            except PyJWTError:
                return False

            admin = result.get('admin', False)

            if not admin:
                return False

            return True
