# tools/search_file_or_folder/api.py

from typing import Dict, Any
import os
import unicodedata
from dotenv import load_dotenv

def search_file_or_folder(
    name: str,
    search_path: str = None,
    search_type: str = "both",
    case_sensitive: bool = True,
    partial_match: bool = False
) -> Dict[str, Any]:
    """
    Searches for files or folders by name, supporting Unicode characters.

    Args:
        name (str): The name of the file or folder to search for.
        search_path (str, optional): The path to start the search from. Defaults to the path from environment variable 'AI_ACCESSIBLE_PATH' or user's home directory.
        search_type (str, optional): Type of search - 'file', 'folder', or 'both'. Defaults to "both".
        case_sensitive (bool, optional): Whether the search is case-sensitive. Defaults to True.
        partial_match (bool, optional): Whether to allow partial name matching. Defaults to False.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        # Load environment variables
        load_dotenv()
        SEARCH_PATH = os.getenv('AI_ACCESSIBLE_PATH')

        # If search_path is None, set it to the user's home directory
        if not search_path:
            search_path = os.path.expanduser("~")

        matched_paths = []

        # Normalize the name to match
        name_to_match = unicodedata.normalize('NFC', name)
        if not case_sensitive:
            name_to_match = name_to_match.casefold()

        valid_search_types = ["file", "folder", "both"]
        if search_type not in valid_search_types:
            return {
                "output": None,
                "error": f"Invalid search_type: {search_type}. Choose from 'file', 'folder', or 'both'.",
                "error_code": "INVALID_SEARCH_TYPE"
            }

        for root, dirs, files in os.walk(search_path):
            # Normalize root path
            root = unicodedata.normalize('NFC', root)

            # Search for directories
            if search_type in ["both", "folder"]:
                for dirname in dirs:
                    dirname_normalized = unicodedata.normalize('NFC', dirname)
                    dirname_to_compare = dirname_normalized
                    if not case_sensitive:
                        dirname_to_compare = dirname_to_compare.casefold()
                    if partial_match:
                        if name_to_match in dirname_to_compare:
                            matched_paths.append(os.path.join(root, dirname_normalized))
                    else:
                        if name_to_match == dirname_to_compare:
                            matched_paths.append(os.path.join(root, dirname_normalized))

            # Search for files
            if search_type in ["both", "file"]:
                for filename in files:
                    filename_normalized = unicodedata.normalize('NFC', filename)
                    filename_to_compare = filename_normalized
                    if not case_sensitive:
                        filename_to_compare = filename_to_compare.casefold()
                    if partial_match:
                        if name_to_match in filename_to_compare:
                            matched_paths.append(os.path.join(root, filename_normalized))
                    else:
                        if name_to_match == filename_to_compare:
                            matched_paths.append(os.path.join(root, filename_normalized))

        return {
            "output": {"matched_paths": matched_paths},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error searching for file or folder: {e}",
            "error_code": "SEARCH_FAILED"
        }