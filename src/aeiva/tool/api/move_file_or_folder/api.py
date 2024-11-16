# toolkit/file_toolkit/move_file_or_folder/api.py

import shutil
import os
from typing import Dict, Any

def move_file_or_folder(source: str, destination: str) -> Dict[str, Any]:
    """
    Moves a file or folder from the source path to the destination path.

    Args:
        source (str): The path of the file or folder to move.
        destination (str): The target path where the file or folder will be moved.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not os.path.exists(source):
            return {
                "output": None,
                "error": f"Source path '{source}' does not exist.",
                "error_code": "SOURCE_NOT_FOUND"
            }
        
        shutil.move(source, destination)
        
        return {
            "output": f"Moved '{source}' to '{destination}' successfully.",
            "error": None,
            "error_code": "SUCCESS"
        }
    except FileNotFoundError:
        return {
            "output": None,
            "error": f"Source path '{source}' not found.",
            "error_code": "SOURCE_NOT_FOUND"
        }
    except PermissionError:
        return {
            "output": None,
            "error": f"Permission denied while moving '{source}' to '{destination}'.",
            "error_code": "PERMISSION_DENIED"
        }
    except shutil.Error as e:
        return {
            "output": None,
            "error": f"Error moving '{source}' to '{destination}': {str(e)}",
            "error_code": "SHUTIL_ERROR"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to move '{source}' to '{destination}': {str(e)}",
            "error_code": "FAILED_TO_MOVE"
        }