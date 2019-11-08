
GET_ACTION_LIST = 'get_action_list'
EXECUTE_ACTION = 'execute_action'
GET_FIELD_OPTIONS = 'get_field_options'
GET_ELEMENT_STATUS = 'get_element_status'

message_handlers = {}


def add_handler(message_name, func):
    message_handlers[message_name] = func


def get_handler(message_name):
    return message_handlers.get(message_name)
