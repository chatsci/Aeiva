# toolkit/system_toolkit/check_internet_connection/api.py

import socket
from typing import Dict, Any

def check_internet_connection(host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0) -> Dict[str, Any]:
    """
    Verifies if the system has an active internet connection.

    Args:
        host (str, optional): Host to connect to. Defaults to "8.8.8.8" (Google DNS).
        port (int, optional): Port to connect to. Defaults to 53.
        timeout (float, optional): Connection timeout in seconds. Defaults to 3.0.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return {
            "output": {"is_connected": True},
            "error": None,
            "error_code": "SUCCESS"
        }
    except socket.error:
        return {
            "output": {"is_connected": False},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to check internet connection: {str(e)}",
            "error_code": "FAILED_TO_CHECK_CONNECTION"
        }