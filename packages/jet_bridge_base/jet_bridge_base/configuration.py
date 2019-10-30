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


configuration = Configuration()


def set_configuration(new_configuration):
    global configuration
    configuration = new_configuration
    set_settings(configuration.get_settings())
