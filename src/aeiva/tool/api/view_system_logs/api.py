# toolkit/system_toolkit/view_system_logs/api.py

import platform
import subprocess
from typing import Dict, Any

def view_system_logs(log_type: str = "system") -> Dict[str, Any]:
    """
    Accesses and retrieves system logs.

    Args:
        log_type (str, optional): Type of logs to retrieve ("system", "application"). Defaults to "system".

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        system = platform.system()
        if system in ["Linux", "Darwin"]:  # Unix-like systems
            if log_type == "system":
                command = ["journalctl", "-n", "100"]  # Last 100 entries
            elif log_type == "application":
                command = ["journalctl", "-u", "application_name", "-n", "100"]  # Replace 'application_name' as needed
            else:
                return {
                    "output": None,
                    "error": f"Unsupported log type: {log_type}",
                    "error_code": "UNSUPPORTED_LOG_TYPE"
                }
        elif system == "Windows":
            if log_type == "system":
                command = ["wevtutil", "qe", "System", "/c:100", "/f:text"]
            elif log_type == "application":
                command = ["wevtutil", "qe", "Application", "/c:100", "/f:text"]
            else:
                return {
                    "output": None,
                    "error": f"Unsupported log type: {log_type}",
                    "error_code": "UNSUPPORTED_LOG_TYPE"
                }
        else:
            return {
                "output": None,
                "error": f"Unsupported operating system: {system}",
                "error_code": "UNSUPPORTED_OS"
            }
        
        # Execute the command
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "output": {"logs": result.stdout},
            "error": None,
            "error_code": "SUCCESS"
        }
    except subprocess.CalledProcessError as e:
        return {
            "output": None,
            "error": f"Failed to retrieve logs: {e.stderr.strip()}",
            "error_code": "FAILED_TO_VIEW_LOGS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to retrieve logs: {str(e)}",
            "error_code": "FAILED_TO_VIEW_LOGS"
        }