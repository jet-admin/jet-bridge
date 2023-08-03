import gc

from jet_bridge_base.db import release_inactive_graphql_schemas


def run_release_inactive_graphql_schemas_task():
    release_inactive_graphql_schemas()
    gc.collect()
