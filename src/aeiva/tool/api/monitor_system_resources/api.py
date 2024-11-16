# toolkit/system_toolkit/monitor_system_resources/api.py

import psutil
from typing import Dict, Any

def monitor_system_resources(interval: float = 1.0) -> Dict[str, Any]:
    """
    Tracks CPU, memory, and other resource usage in real-time.

    Args:
        interval (float, optional): Time in seconds between each resource check. Defaults to 1.0.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=interval)
        virtual_memory = psutil.virtual_memory()
        swap_memory = psutil.swap_memory()
        disk_usage = {partition.mountpoint: psutil.disk_usage(partition.mountpoint)._asdict() for partition in psutil.disk_partitions()}
        network_io = psutil.net_io_counters()._asdict()

        resources = {
            "cpu_percent": cpu_percent,
            "virtual_memory": {
                "total": virtual_memory.total,
                "available": virtual_memory.available,
                "percent": virtual_memory.percent,
                "used": virtual_memory.used,
                "free": virtual_memory.free
            },
            "swap_memory": {
                "total": swap_memory.total,
                "used": swap_memory.used,
                "free": swap_memory.free,
                "percent": swap_memory.percent
            },
            "disk_usage": disk_usage,
            "network_io": network_io
        }

        return {
            "output": {"resources": resources},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to monitor system resources: {str(e)}",
            "error_code": "FAILED_TO_MONITOR_RESOURCES"
        }