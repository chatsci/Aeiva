import os
import unicodedata
from dotenv import load_dotenv

SEARCH_PATH = os.getenv('AI_ACCESSIBLE_PATH')

def search_file_or_folder(
    name: str,
    search_path: str = SEARCH_PATH,
    search_type: str = "both",
    case_sensitive: bool = True,
    partial_match: bool = False
) -> dict:
    """
    Search for files or folders by name, supporting Unicode characters.

    Args:
        name (str): The name of the file or folder to search for.
        search_path (str): The path to start the search from. Defaults to the user's home directory.
        search_type (str): Type of search - 'file', 'folder', or 'both'.
        case_sensitive (bool): Whether the search is case-sensitive.
        partial_match (bool): Whether to allow partial name matching.

    Returns:
        dict: A dictionary containing the list of matched paths.
    """
    import sys

    # If search_path is None, set it to the user's home directory
    if search_path is None:
        search_path = os.path.expanduser("~")

    matched_paths = []

    # Normalize the name to match
    name_to_match = unicodedata.normalize('NFC', name)
    if not case_sensitive:
        name_to_match = name_to_match.casefold()

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

    return {"matched_paths": matched_paths}

# print(search_file_or_folder("S.H.E-沿海公路的出口", partial_match=True))