# api.py

from typing import Dict, Any
import os

def rename_file(old_file_path: str, new_file_path: str) -> Dict[str, Any]:
    """
    Renames a file from old_file_path to new_file_path.

    Args:
        old_file_path (str): The current path of the file.
        new_file_path (str): The new path for the file.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not old_file_path.strip() or not new_file_path.strip():
            return {
                "output": None,
                "error": "Both old_file_path and new_file_path must be provided.",
                "error_code": "MISSING_PATHS"
            }

        resolved_old_path = os.path.abspath(os.path.expanduser(old_file_path))
        resolved_new_path = os.path.abspath(os.path.expanduser(new_file_path))
        new_dir = os.path.dirname(resolved_new_path)

        if not os.path.exists(resolved_old_path):
            return {
                "output": None,
                "error": f"File not found: {resolved_old_path}",
                "error_code": "FILE_NOT_FOUND"
            }

        if os.path.exists(resolved_new_path):
            return {
                "output": None,
                "error": f"Destination already exists: {resolved_new_path}",
                "error_code": "DESTINATION_EXISTS"
            }

        # Ensure the destination directory exists
        if not os.path.exists(new_dir):
            try:
                os.makedirs(new_dir, exist_ok=True)
            except PermissionError as e:
                return {
                    "output": None,
                    "error": f"Permission denied while creating directories: {e}",
                    "error_code": "PERMISSION_DENIED"
                }
            except OSError as e:
                return {
                    "output": None,
                    "error": f"OS error while creating directories: {e}",
                    "error_code": "OS_ERROR"
                }

        os.rename(resolved_old_path, resolved_new_path)

        return {
            "output": f"File renamed from {resolved_old_path} to {resolved_new_path}",
            "error": None,
            "error_code": "SUCCESS"
        }

    except PermissionError as e:
        return {
            "output": None,
            "error": f"Permission denied: {e}",
            "error_code": "PERMISSION_DENIED"
        }
    except FileExistsError as e:
        return {
            "output": None,
            "error": f"Destination already exists: {e}",
            "error_code": "DESTINATION_EXISTS"
        }
    except FileNotFoundError as e:
        return {
            "output": None,
            "error": f"File not found: {e}",
            "error_code": "FILE_NOT_FOUND"
        }
    except OSError as e:
        return {
            "output": None,
            "error": f"OS error occurred: {e}",
            "error_code": "OS_ERROR"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Unexpected error: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }