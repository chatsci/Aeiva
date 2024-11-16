# toolkit/system_toolkit/get_disk_usage/api.py

import psutil
from typing import Dict, Any

def get_disk_usage(path: str = "/") -> Dict[str, Any]:
    """
    Provides information on disk space usage.

    Args:
        path (str, optional): The path to check disk usage for. Defaults to root '/'.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        usage = psutil.disk_usage(path)
        disk_info = {
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent": usage.percent
        }
        return {
            "output": {"disk_usage": disk_info},
            "error": None,
            "error_code": "SUCCESS"
        }
    except FileNotFoundError:
        return {
            "output": None,
            "error": f"The path '{path}' does not exist.",
            "error_code": "PATH_NOT_FOUND"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to get disk usage for path '{path}': {str(e)}",
            "error_code": "FAILED_TO_GET_DISK_USAGE"
        }