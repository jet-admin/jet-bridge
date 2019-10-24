
GET_ACTION_LIST = 'get_action_list'
EXECUTE_ACTION = 'execute_action'

message_handlers = {}


def add_handler(message_name, func):
    message_handlers[message_name] = func


def get_handler(message_name):
    return message_handlers.get(message_name)
