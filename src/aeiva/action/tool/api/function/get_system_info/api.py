# tools/get_system_info/api.py

import platform
import psutil

def get_system_info() -> dict:
    """
    Retrieve system information.

    Returns:
        dict: A dictionary containing system information.
    """
    try:
        info = {
            'os': platform.system(),
            'os_version': platform.version(),
            'cpu_count': psutil.cpu_count(),
            'memory': psutil.virtual_memory().total,
            'disk_usage': psutil.disk_usage('/').total
        }
        return info
    except Exception as e:
        return {"error": f"Error retrieving system information: {e}"}