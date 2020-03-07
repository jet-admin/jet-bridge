import json

from jet_bridge_base import settings
from jet_bridge_base.utils.backend import project_auth


class BasePermission(object):

    def has_permission(self, view):
        return True

    def has_object_permission(self, view, obj):
        return True


class HasProjectPermissions(BasePermission):
    token_prefix = 'Token '
    project_token_prefix = 'ProjectToken '

    def has_permission(self, view):
        # return True
        token = view.request.headers.get('AUTHORIZATION')
        permission = view.required_project_permission() if hasattr(view, 'required_project_permission') else None

        if not token:
            return False

        bridge_settings_encoded = view.request.headers.get('X_BRIDGE_SETTINGS')

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

        if token[:len(self.token_prefix)] == self.token_prefix:
            token = token[len(self.token_prefix):]

            result = project_auth(token, project_token, permission)

            # if result.get('warning'):
            #     view.headers['X-Application-Warning'] = result['warning']

            return result['result']
        elif token[:len(self.project_token_prefix)] == self.project_token_prefix:
            token = token[len(self.project_token_prefix):]

            result = project_auth(token, project_token, permission)

            # if result.get('warning'):
            #     view.headers['X-Application-Warning'] = result['warning']

            return result['result']
        else:
            return False


class ReadOnly(BasePermission):

    def has_permission(self, view):
        if not settings.READ_ONLY:
            return True
        if view.action in ['create', 'update', 'partial_update', 'destroy']:
            return False
        return True
