# tools/open_file_or_folder/api.py

import os
import subprocess
import sys

def open_file_or_folder(path: str) -> str:
    """
    Open a file or folder with the default application.

    Args:
        path (str): The path to the file or folder.

    Returns:
        str: A message indicating the result.
    """
    if not os.path.exists(path):
        return f"Path not found: {path}"

    try:
        if sys.platform.startswith('win'):
            os.startfile(path)
        elif sys.platform.startswith('darwin'):
            subprocess.run(['open', path], check=True)
        elif sys.platform.startswith('linux'):
            subprocess.run(['xdg-open', path], check=True)
        else:
            return "Unsupported operating system."
        return f"Opened: {path}"
    except Exception as e:
        return f"Failed to open '{path}': {e}"