# tools/list_files/api.py

from typing import Dict, Any
import os

def list_files(directory: str = None) -> Dict[str, Any]:
    """
    Lists files and directories in a specified path.

    Args:
        directory (str, optional): The directory to list files from. Defaults to the user's home directory.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if directory is None:
            directory = os.path.expanduser("~")
        else:
            directory = os.path.expanduser(directory)

        if not os.path.isdir(directory):
            return {
                "output": None,
                "error": f"Directory not found: {directory}",
                "error_code": "DIRECTORY_NOT_FOUND"
            }

        items = os.listdir(directory)
        return {
            "output": {"items": items},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error listing files: {e}",
            "error_code": "LIST_FILES_FAILED"
        }