# toolkit/system_toolkit/get_system_info/api.py

import platform
import psutil
from typing import Dict, Any

def get_system_info() -> Dict[str, Any]:
    """
    Retrieves comprehensive system information.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        uname = platform.uname()
        system_info = {
            "system": uname.system,
            "node_name": uname.node,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "processor": uname.processor,
            "python_version": platform.python_version(),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "cpu_freq_current": psutil.cpu_freq().current if psutil.cpu_freq() else None,
            "total_memory": psutil.virtual_memory().total,
            "available_memory": psutil.virtual_memory().available,
            "used_memory": psutil.virtual_memory().used,
            "memory_percent": psutil.virtual_memory().percent,
            "swap_total": psutil.swap_memory().total,
            "swap_used": psutil.swap_memory().used,
            "swap_free": psutil.swap_memory().free,
            "swap_percent": psutil.swap_memory().percent,
            "disk_partitions": [
                {
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "opts": part.opts
                } for part in psutil.disk_partitions()
            ],
            "disk_usage": {
                part.mountpoint: {
                    "total": psutil.disk_usage(part.mountpoint).total,
                    "used": psutil.disk_usage(part.mountpoint).used,
                    "free": psutil.disk_usage(part.mountpoint).free,
                    "percent": psutil.disk_usage(part.mountpoint).percent
                } for part in psutil.disk_partitions()
            },
            "network_interfaces": {iface: [addr.address for addr in addrs] for iface, addrs in psutil.net_if_addrs().items()},
            "network_stats": {
                iface: {
                    "is_up": stats.isup,
                    "duplex": stats.duplex.name if stats.duplex else "UNKNOWN",
                    "speed": stats.speed,
                    "mtu": stats.mtu
                } for iface, stats in psutil.net_if_stats().items()
            }
        }

        return {
            "output": {"system_info": system_info},
            "error": None,
            "error_code": "SUCCESS"
        }

    except Exception as e:
        return {
            "output": None,
            "error": f"An unexpected error occurred: {str(e)}",
            "error_code": "UNEXPECTED_ERROR"
        }