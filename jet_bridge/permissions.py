from jet_bridge.db import Session

from jet_bridge import settings
from jet_bridge.utils.backend import project_auth


class BasePermission(object):

    def has_permission(self, view):
        return True

    def has_object_permission(self, view, obj):
        return True


class HasProjectPermissions(BasePermission):
    token_prefix = 'Token '
    project_token_prefix = 'ProjectToken '

    def has_permission(self, view):
        token = view.request.headers.get('Authorization')
        session_create = not getattr(view, 'session')
        permission = getattr(view, 'required_project_permission', None)

        if not token:
            return False

        try:
            session = Session() if session_create else getattr(view, 'session')

            if token[:len(self.token_prefix)] == self.token_prefix:
                token = token[len(self.token_prefix):]

                result = project_auth(session, token, permission)

                if result.get('warning'):
                    view.headers['X-Application-Warning'] = result['warning']

                return result['result']
            elif token[:len(self.project_token_prefix)] == self.project_token_prefix:
                token = token[len(self.project_token_prefix):]

                result = project_auth(session, token, permission)

                if result.get('warning'):
                    view.headers['X-Application-Warning'] = result['warning']

                return result['result']
            else:
                return False
        finally:
            if session_create:
                session.close()


class ModifyNotInDemo(BasePermission):

    def has_permission(self, view):
        if not settings.READ_ONLY:
            return True
        # if view.action in ['create', 'update', 'partial_update', 'destroy']:
        #     return False
        if view.request.method.lower() in ['post', 'put', 'patch', 'delete']:
            return False
        return True
