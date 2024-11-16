# toolkit/system_toolkit/delete_user/api.py

import subprocess
import platform
from typing import Dict, Any

def delete_user(username: str) -> Dict[str, Any]:
    """
    Removes an existing user from the system.

    Args:
        username (str): The username of the user to remove.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        system = platform.system()
        if system in ["Linux", "Darwin"]:  # Unix-like systems
            command = ["sudo", "userdel", "-r", username]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        elif system == "Windows":
            # Windows user deletion using net user command
            command = ["net", "user", username, "/delete"]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            return {
                "output": None,
                "error": f"Unsupported operating system: {system}",
                "error_code": "UNSUPPORTED_OS"
            }
        
        return {
            "output": f"User '{username}' deleted successfully.",
            "error": None,
            "error_code": "SUCCESS"
        }
    except subprocess.CalledProcessError as e:
        return {
            "output": None,
            "error": f"Failed to delete user '{username}': {e.stderr.strip()}",
            "error_code": "FAILED_TO_DELETE_USER"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to delete user '{username}': {str(e)}",
            "error_code": "FAILED_TO_DELETE_USER"
        }