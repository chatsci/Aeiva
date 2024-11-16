# toolkit/system_toolkit/change_user_password/api.py

import subprocess
import platform
from typing import Dict, Any

def change_user_password(username: str, new_password: str) -> Dict[str, Any]:
    """
    Updates a user’s password.

    Args:
        username (str): The username of the user.
        new_password (str): The new password to set.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        system = platform.system()
        if system in ["Linux", "Darwin"]:  # Unix-like systems
            # Using chpasswd for Linux and macOS
            command = ["sudo", "chpasswd"]
            input_str = f"{username}:{new_password}"
            subprocess.run(command, input=input_str, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        elif system == "Windows":
            # Using net user for Windows
            command = ["net", "user", username, new_password]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            return {
                "output": None,
                "error": f"Unsupported operating system: {system}",
                "error_code": "UNSUPPORTED_OS"
            }
        
        return {
            "output": f"Password for user '{username}' updated successfully.",
            "error": None,
            "error_code": "SUCCESS"
        }
    except subprocess.CalledProcessError as e:
        return {
            "output": None,
            "error": f"Failed to change password for user '{username}': {e.stderr.strip()}",
            "error_code": "FAILED_TO_CHANGE_PASSWORD"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to change password for user '{username}': {str(e)}",
            "error_code": "FAILED_TO_CHANGE_PASSWORD"
        }