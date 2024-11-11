# tools/write_file/api.py

import os

def write_file(file_path: str, content: str) -> str:
    """
    Write content to a file.

    Args:
        file_path (str): The path to the file.
        content (str): The content to write into the file.

    Returns:
        str: A message indicating the result.
    """
    try:
        file_path = os.path.expanduser(file_path)
        directory = os.path.dirname(file_path)

        # Ensure the directory exists and is writable
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Content written to {file_path}"
    except Exception as e:
        return f"Error writing to file: {e}"