# tools/delete_file/api.py

import os

def delete_file(file_path: str, confirm: bool = False) -> str:
    """
    Delete a specified file after confirmation.

    Args:
        file_path (str): The path to the file.
        confirm (bool): Confirmation flag to proceed with deletion.

    Returns:
        str: A message indicating the result.
    """
    try:
        file_path = os.path.expanduser(file_path)

        if not os.path.isfile(file_path):
            return f"File not found: {file_path}"

        if not confirm:
            return "Deletion not confirmed. Set 'confirm' to True to delete the file."

        os.remove(file_path)
        return f"File deleted: {file_path}"
    except Exception as e:
        return f"Error deleting file: {e}"