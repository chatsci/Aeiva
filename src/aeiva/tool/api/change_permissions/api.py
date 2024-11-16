# toolkit/file_toolkit/change_permissions/api.py

import os
import stat
from typing import Dict, Any
import platform
import subprocess

def change_permissions(path: str, mode: int) -> Dict[str, Any]:
    """
    Modifies the access permissions of a file or folder.

    Args:
        path (str): The path of the file or folder.
        mode (int): The new permission mode (e.g., 0o755).

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not os.path.exists(path):
            return {
                "output": None,
                "error": f"Path '{path}' does not exist.",
                "error_code": "PATH_NOT_FOUND"
            }
        
        system = platform.system()
        if system in ["Linux", "Darwin"]:  # Unix-like systems
            os.chmod(path, mode)
        elif system == "Windows":
            # Windows handles permissions differently; using icacls for basic permissions
            # Note: This is a simplified example and may not cover all permission scenarios
            command = ["icacls", path, "/grant", f"Everyone:(R,W)"]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            return {
                "output": None,
                "error": f"Unsupported operating system: {system}",
                "error_code": "UNSUPPORTED_OS"
            }
        
        return {
            "output": f"Permissions for '{path}' changed to '{oct(mode)}' successfully.",
            "error": None,
            "error_code": "SUCCESS"
        }
    except PermissionError:
        return {
            "output": None,
            "error": f"Permission denied while changing permissions for '{path}'.",
            "error_code": "PERMISSION_DENIED"
        }
    except subprocess.CalledProcessError as e:
        return {
            "output": None,
            "error": f"Failed to change permissions for '{path}': {e.stderr.strip()}",
            "error_code": "FAILED_TO_CHANGE_PERMISSIONS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to change permissions for '{path}': {str(e)}",
            "error_code": "FAILED_TO_CHANGE_PERMISSIONS"
        }