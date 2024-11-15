# api.py

from typing import Dict, Any, Optional
import os

def create_file_or_folder(path: str, is_directory: bool = False) -> Dict[str, Any]:
    """
    Creates a new file or directory at the specified path.

    Args:
        path (str): The path to create. If is_directory is False, creates a file.
                    If is_directory is True, creates a directory.
        is_directory (bool, optional): Whether to create a directory. Defaults to False.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not path.strip():
            return {
                "output": None,
                "error": "Path cannot be empty or just whitespace.",
                "error_code": "EMPTY_PATH"
            }

        # Resolve the absolute path
        resolved_path = os.path.abspath(os.path.expanduser(path))
        parent_dir = os.path.dirname(resolved_path)

        # Ensure the parent directory exists
        if not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
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

        if is_directory:
            if os.path.exists(resolved_path):
                return {
                    "output": None,
                    "error": f"Directory already exists: {resolved_path}",
                    "error_code": "DIRECTORY_EXISTS"
                }
            os.makedirs(resolved_path, exist_ok=True)
            return {
                "output": f"Directory created at {resolved_path}",
                "error": None,
                "error_code": "SUCCESS"
            }
        else:
            if os.path.exists(resolved_path):
                return {
                    "output": None,
                    "error": f"File already exists: {resolved_path}",
                    "error_code": "FILE_EXISTS"
                }
            with open(resolved_path, 'w', encoding='utf-8') as f:
                pass  # Create an empty file
            return {
                "output": f"File created at {resolved_path}",
                "error": None,
                "error_code": "SUCCESS"
            }

    except PermissionError as e:
        return {
            "output": None,
            "error": f"Permission denied: {e}",
            "error_code": "PERMISSION_DENIED"
        }
    except FileNotFoundError as e:
        return {
            "output": None,
            "error": f"Directory not found: {e}",
            "error_code": "DIRECTORY_NOT_FOUND"
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