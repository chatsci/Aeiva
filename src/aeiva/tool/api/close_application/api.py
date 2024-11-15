# tools/close_application/api.py

from typing import Dict, Any
import psutil

def close_application(process_name: str) -> Dict[str, Any]:
    """
    Closes an application gracefully.

    Args:
        process_name (str): The name of the process to terminate.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not process_name:
            return {
                "output": None,
                "error": "Process name must be provided.",
                "error_code": "MISSING_PROCESS_NAME"
            }

        found = False
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == process_name:
                proc.terminate()
                found = True

        if found:
            return {
                "output": f"Application '{process_name}' terminated.",
                "error": None,
                "error_code": "SUCCESS"
            }
        else:
            return {
                "output": None,
                "error": f"No running application found with name '{process_name}'.",
                "error_code": "PROCESS_NOT_FOUND"
            }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error closing application: {e}",
            "error_code": "CLOSE_APPLICATION_FAILED"
        }