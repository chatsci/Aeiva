# tools/list_files/api.py

import os

def list_files(directory: str = None) -> dict:
    """
    List files and directories in a specified path.

    Args:
        directory (str): The directory to list files from.

    Returns:
        dict: A dictionary containing the list of files and directories.
    """
    try:
        if directory is None:
            directory = os.path.expanduser("~")
        else:
            directory = os.path.expanduser(directory)

        if not os.path.isdir(directory):
            return {"error": f"Directory not found: {directory}"}

        items = os.listdir(directory)
        return {"items": items}
    except Exception as e:
        return {"error": f"Error listing files: {e}"}