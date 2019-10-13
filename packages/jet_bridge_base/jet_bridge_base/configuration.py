

class Configuration(object):

    def get_model_description(self, db_table):
        pass

    def get_hidden_model_description(self):
        return []

configuration = Configuration()


def set_configuration(new_configuration):
    global configuration
    configuration = new_configuration
