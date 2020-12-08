import json

from jet_bridge_base import settings
from jet_bridge_base.utils.backend import project_auth


class BasePermission(object):

    def has_permission(self, view, request):
        return True

    def has_object_permission(self, view, request, obj):
        return True


class HasProjectPermissions(BasePermission):
    user_token_prefix = 'Token'
    project_token_prefix = 'ProjectToken'

    def parse_token(self, value):
        try:
            type, data = value.split(' ', 2)
            items = data.split(';')

            if len(items) == 0:
                return

            try:
                params = dict(map(lambda x: x.split('=', 2), items[1:]))
            except ValueError:
                params = {}

            return {
                'type': type,
                'value': items[0],
                'params': params
            }
        except (ValueError, AttributeError):
            pass

    def has_permission(self, view, request):
        # return True
        token = self.parse_token(request.headers.get('AUTHORIZATION'))
        permission = view.required_project_permission(request) if hasattr(view, 'required_project_permission') else None

        if not token:
            return False

        bridge_settings_encoded = request.headers.get('X_BRIDGE_SETTINGS')

        if bridge_settings_encoded:
            from jet_bridge_base.utils.crypt import decrypt

            try:
                secret_key = settings.TOKEN.replace('-', '').lower()
                bridge_settings = json.loads(decrypt(bridge_settings_encoded, secret_key))
            except Exception:
                bridge_settings = {}

            project_token = bridge_settings.get('token')
        else:
            project_token = settings.TOKEN

        if token['type'] == self.user_token_prefix:
            result = project_auth(token['value'], project_token, permission, token['params'])

            # if result.get('warning'):
            #     view.headers['X-Application-Warning'] = result['warning']

            return result['result']
        elif token['type'] == self.project_token_prefix:
            result = project_auth(token['value'], project_token, permission, token['params'])

            # if result.get('warning'):
            #     view.headers['X-Application-Warning'] = result['warning']

            return result['result']
        else:
            return False


class ReadOnly(BasePermission):

    def has_permission(self, view, request):
        if not settings.READ_ONLY:
            return True
        if request.action in ['create', 'update', 'partial_update', 'destroy']:
            return False
        return True
