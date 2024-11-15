# tools/open_application/api.py

from typing import Dict, Any
import os
import subprocess
import sys

def open_application(application_path: str) -> Dict[str, Any]:
    """
    Launches an application.

    Args:
        application_path (str): The path to the application executable.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not application_path:
            return {
                "output": None,
                "error": "Application path must be provided.",
                "error_code": "MISSING_APPLICATION_PATH"
            }
        
        application_path = os.path.expanduser(application_path)

        if not os.path.exists(application_path):
            return {
                "output": None,
                "error": f"Application not found: {application_path}",
                "error_code": "APPLICATION_NOT_FOUND"
            }

        if sys.platform.startswith('win'):
            os.startfile(application_path)
        elif sys.platform.startswith('darwin') or sys.platform.startswith('linux'):
            subprocess.Popen([application_path])
        else:
            return {
                "output": None,
                "error": "Unsupported operating system.",
                "error_code": "UNSUPPORTED_OS"
            }
        return {
            "output": f"Application opened: {application_path}",
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error opening application: {e}",
            "error_code": "OPEN_APPLICATION_FAILED"
        }