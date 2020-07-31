from social_core.storage import BaseStorage, UserMixin


class User(object):
    social_user = None
    is_new = True
    details = None
    extra_data = None


class UserController(UserMixin):

    @classmethod
    def user_model(cls):
        return User


class JetBridgeStorage(BaseStorage):
    user = UserController
