# tools/read_file/api.py

import os

def read_file(file_path: str) -> str:
    """
    Read the contents of a file.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The content of the file or an error message.
    """
    try:
        file_path = os.path.expanduser(file_path)

        if not os.path.isfile(file_path):
            return f"File not found: {file_path}"

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading file: {e}"