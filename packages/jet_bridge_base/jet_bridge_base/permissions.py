from jet_bridge_base import settings
from jet_bridge_base.sentry import sentry_controller
from jet_bridge_base.utils.backend import project_auth
from jet_bridge_base.utils.crypt import get_sha256_hash
from jet_bridge_base.utils.token import decompress_permissions, parse_token, JWT_TOKEN_PREFIX, USER_TOKEN_PREFIX, \
    PROJECT_TOKEN_PREFIX, BEARER_TOKEN_PREFIX, decode_jwt_token


class BasePermission(object):

    def has_permission(self, view, request):
        return True

    def has_object_permission(self, view, request, obj):
        return True


class HasProjectPermissions(BasePermission):
    def has_view_permissions(self, view_permissions, user_permissions, project_token):
        if not view_permissions:
            return True
        elif user_permissions.get('owner'):
            return True
        elif user_permissions.get('super_group'):
            return True

        if 'permissions' in user_permissions:
            permissions = decompress_permissions(user_permissions['permissions'])
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

        if not project_token:
            return False

        token_hash = get_sha256_hash(project_token.replace('-', '').lower())

        for item in permissions:
            item_type = item.get('permission_type', '')
            item_object = item.get('permission_object', '')
            item_actions = item.get('permission_actions', '')

            if view_permission_type == 'model':
                resource_token_hash = item.get('resource_token_hash', '')
                item_object_model = item_object.split('.', 1)[-1:][0]

                # TODO: make check non optional
                if resource_token_hash and resource_token_hash != token_hash:
                    continue

                if item_type != view_permission_type or item_object_model != view_permission_object:
                    continue
            else:
                if item_type != view_permission_type or item_object != view_permission_object:
                    continue

            if view_permission_actions in item_actions:
                return True

        return False

    def has_permission(self, view, request):
        token = parse_token(request.headers.get('AUTHORIZATION'))
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

        if token['type'] == JWT_TOKEN_PREFIX:
            result = decode_jwt_token(token['value'])

            if result is None:
                return False

            user_permissions = result.get('projects', {}).get(project)

            if user_permissions is None:
                return False

            request.project = result.get('project')
            request.environment = result.get('environment')
            request.resource_token = project_token
            request.sso_shared_data = result.get('sso_shared_data')

            user_id = result.get('user')
            if user_id is not None:
                sentry_controller.set_user({'id': user_id})
            else:
                sentry_controller.set_user(None)

            return self.has_view_permissions(view_permissions, user_permissions, project_token)
        elif token['type'] == USER_TOKEN_PREFIX:
            result = project_auth(token['value'], project_token, view_permissions, token['params'])

            # if result.get('warning'):
            #     view.headers['X-Application-Warning'] = result['warning']

            return result['result']
        elif token['type'] == PROJECT_TOKEN_PREFIX:
            result = project_auth(token['value'], project_token, view_permissions, token['params'])

            # if result.get('warning'):
            #     view.headers['X-Application-Warning'] = result['warning']

            return result['result']
        elif token['type'] == BEARER_TOKEN_PREFIX:
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
            result = decode_jwt_token(key)

            if result is None:
                return False

            admin = result.get('admin', False)

            if not admin:
                return False

            return True
