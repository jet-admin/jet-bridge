from jet_bridge_base.settings import set_settings


class Configuration(object):

    def get_version(self):
        pass

    def get_model_description(self, db_table):
        pass

    def get_hidden_model_description(self):
        return []

    def get_settings(self):
        pass

configuration = Configuration()


def set_configuration(new_configuration):
    global configuration
    configuration = new_configuration
    set_settings(configuration.get_settings())
