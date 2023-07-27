import psutil
from jet_bridge_base.utils.common import format_size


def get_memory_usage():
    process = psutil.Process()
    return process.memory_info().rss


def get_memory_usage_human():
    memory_used = get_memory_usage()
    return format_size(memory_used)
