# toolkit/file_toolkit/copy_file_or_folder/api.py

import shutil
import os
from typing import Dict, Any

def copy_file_or_folder(source: str, destination: str) -> Dict[str, Any]:
    """
    Copies a file or folder from the source path to the destination path.

    Args:
        source (str): The path of the file or folder to copy.
        destination (str): The target path where the file or folder will be copied.

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
        
        if os.path.isdir(source):
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        
        return {
            "output": f"Copied '{source}' to '{destination}' successfully.",
            "error": None,
            "error_code": "SUCCESS"
        }
    except FileExistsError:
        return {
            "output": None,
            "error": f"Destination '{destination}' already exists.",
            "error_code": "DESTINATION_EXISTS"
        }
    except PermissionError:
        return {
            "output": None,
            "error": f"Permission denied while copying '{source}' to '{destination}'.",
            "error_code": "PERMISSION_DENIED"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to copy '{source}' to '{destination}': {str(e)}",
            "error_code": "FAILED_TO_COPY"
        }