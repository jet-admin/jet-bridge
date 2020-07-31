from social_core.backends.utils import load_backends
from social_core.utils import get_strategy


STRATEGY_PATH = 'jet_bridge_base.external_auth.strategy.JetBridgeStrategy'
STORAGE_PATH = 'jet_bridge_base.external_auth.storage.JetBridgeStorage'


def load_strategy(request_handler, config):
    return get_strategy(STRATEGY_PATH, STORAGE_PATH, request_handler, config)


def load_backends_classes(backend_paths):
    backends = load_backends(backend_paths, force_load=True)

    return dict(map(lambda x: (backend_paths[x[0]], x[1]), enumerate(backends.values())))

