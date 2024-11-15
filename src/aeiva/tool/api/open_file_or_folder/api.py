# tools/open_file_or_folder/api.py

from typing import Dict, Any
import os
import subprocess
import sys

def open_file_or_folder(path: str) -> Dict[str, Any]:
    """
    Opens a file or folder with the default application.

    Args:
        path (str): The path to the file or folder.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not path:
            return {
                "output": None,
                "error": "Path must be provided.",
                "error_code": "MISSING_PATH"
            }
        
        path = os.path.expanduser(path)

        if not os.path.exists(path):
            return {
                "output": None,
                "error": f"Path not found: {path}",
                "error_code": "PATH_NOT_FOUND"
            }

        if sys.platform.startswith('win'):
            os.startfile(path)
        elif sys.platform.startswith('darwin'):
            subprocess.run(['open', path], check=True)
        elif sys.platform.startswith('linux'):
            subprocess.run(['xdg-open', path], check=True)
        else:
            return {
                "output": None,
                "error": "Unsupported operating system.",
                "error_code": "UNSUPPORTED_OS"
            }
        return {
            "output": f"Opened: {path}",
            "error": None,
            "error_code": "SUCCESS"
        }
    except subprocess.CalledProcessError as e:
        return {
            "output": None,
            "error": f"Failed to open '{path}': {e}",
            "error_code": "OPEN_FAILED"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to open '{path}': {e}",
            "error_code": "OPEN_FAILED"
        }