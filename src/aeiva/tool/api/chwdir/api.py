# api.py

from typing import Dict, Any
import os

def chwdir(path: str) -> Dict[str, Any]:
    """
    Changes the current working directory to the specified path.

    Args:
        path (str): The path to change the current working directory to. 
                    Can be absolute, relative to the current working directory, 
                    or use '..' to navigate up the directory tree.

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
        new_path = os.path.abspath(os.path.expanduser(path))

        # Change the directory
        os.chdir(new_path)

        return {
            "output": f"Changed working directory to {new_path}",
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
    except RuntimeError as e:
        return {
            "output": None,
            "error": f"Unable to resolve path: {e}",
            "error_code": "RUNTIME_ERROR"
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