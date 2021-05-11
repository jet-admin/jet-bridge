from jet_bridge_base.settings import set_settings


class Configuration(object):

    def get_type(self):
        pass

    def get_version(self):
        pass

    def get_model_description(self, db_table):
        pass

    def get_hidden_model_description(self):
        return []

    def get_settings(self):
        pass

    def on_model_pre_create(self, model, pk):
        pass

    def on_model_post_create(self, model, instance):
        pass

    def on_model_pre_update(self, model, instance):
        pass

    def on_model_post_update(self, model, instance):
        pass

    def on_model_pre_delete(self, model, instance):
        pass

    def on_model_post_delete(self, model, instance):
        pass

    def media_get_available_name(self, path):
        pass

    def media_exists(self, path):
        pass

    def media_listdir(self, path):
        pass

    def media_get_modified_time(self, path):
        pass

    def media_open(self, path, mode='rb'):
        pass

    def media_save(self, path, content):
        pass

    def media_delete(self, path):
        pass

    def media_url(self, path, request):
        pass

    def session_set(self, request, name, value, secure=True):
        pass

    def session_get(self, request, name, default=None, decode=True, secure=True):
        pass

    def session_clear(self, request, name):
        pass

    def clean_sso_application_name(self, name):
        return name.lower().replace('-', '')

    def clean_sso_applications(self, applications):
        return dict(map(lambda x: (self.clean_sso_application_name(x[0]), x[1]), applications.items()))


configuration = Configuration()


def set_configuration(new_configuration):
    global configuration
    configuration = new_configuration
    set_settings(configuration.get_settings())
