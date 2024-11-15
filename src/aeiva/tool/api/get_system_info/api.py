# tools/get_system_info/api.py

from typing import Dict, Any
import platform
import psutil

def get_system_info() -> Dict[str, Any]:
    """
    Retrieves system information.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        info = {
            'os': platform.system(),
            'os_version': platform.version(),
            'cpu_count': psutil.cpu_count(logical=True),
            'memory': psutil.virtual_memory().total,
            'disk_usage': psutil.disk_usage('/').total
        }
        return {
            "output": info,
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error retrieving system information: {e}",
            "error_code": "GET_SYSTEM_INFO_FAILED"
        }