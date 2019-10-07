from jet_bridge_base.messages import GET_ACTION_LIST, EXECUTE_ACTION

message_handlers = {}


def add_handler(message_name, func):
    message_handlers[message_name] = func


def get_handler(message_name):
    return message_handlers.get(message_name)
