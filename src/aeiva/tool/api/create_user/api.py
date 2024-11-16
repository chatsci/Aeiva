# toolkit/system_toolkit/create_user/api.py

import subprocess
import platform
from typing import Dict, Any

def create_user(username: str, password: str) -> Dict[str, Any]:
    """
    Adds a new user to the system.

    Args:
        username (str): The username for the new user.
        password (str): The password for the new user.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        system = platform.system()
        if system in ["Linux", "Darwin"]:  # Unix-like systems
            command = ["sudo", "useradd", "-m", "-s", "/bin/bash", username]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # Set password
            command = ["sudo", "chpasswd"]
            input_str = f"{username}:{password}"
            subprocess.run(command, input=input_str, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        elif system == "Windows":
            # Windows user creation using net user command
            command = ["net", "user", username, password, "/add"]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            return {
                "output": None,
                "error": f"Unsupported operating system: {system}",
                "error_code": "UNSUPPORTED_OS"
            }
        
        return {
            "output": f"User '{username}' created successfully.",
            "error": None,
            "error_code": "SUCCESS"
        }
    except subprocess.CalledProcessError as e:
        return {
            "output": None,
            "error": f"Failed to create user '{username}': {e.stderr.strip()}",
            "error_code": "FAILED_TO_CREATE_USER"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to create user '{username}': {str(e)}",
            "error_code": "FAILED_TO_CREATE_USER"
        }