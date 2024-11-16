# toolkit/system_toolkit/list_processes/api.py

import psutil
from typing import Dict, Any

def list_processes() -> Dict[str, Any]:
    """
    Lists all currently running processes.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            processes.append(proc.info)
        
        return {
            "output": {"processes": processes},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"An unexpected error occurred: {str(e)}",
            "error_code": "UNEXPECTED_ERROR"
        }