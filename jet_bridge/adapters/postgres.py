from jet_bridge.adapters.base import Adapter, registered_adapters


class PostgresAdapter(Adapter):
    pass

registered_adapters['postgres'] = PostgresAdapter
