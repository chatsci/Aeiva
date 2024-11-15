# api.py

from typing import Dict, Any, List, Tuple, Optional
import os
import fnmatch

def grep(
    word: str,
    pattern: Optional[str] = None,
    recursive: bool = True,
    case_insensitive: bool = True
) -> Dict[str, Any]:
    """
    Searches for a specific word or phrase across multiple files based on a pattern.

    Args:
        word (str): The term to search for.
        pattern (Optional[str]): The file, directory, or glob pattern to search in.
                                  If not provided, searches in the current working directory.
        recursive (bool): If True, search recursively in subdirectories.
        case_insensitive (bool): If True, perform case-insensitive search.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not word:
            return {
                "output": None,
                "error": "Search word must be provided.",
                "error_code": "MISSING_WORD"
            }

        # Determine the root directory
        root_dir = os.getcwd()

        # If pattern is provided, resolve it
        if pattern:
            resolved_pattern = os.path.abspath(os.path.expanduser(pattern))
            if os.path.isdir(resolved_pattern):
                search_dir = resolved_pattern
                search_pattern = "**/*" if recursive else "*"
            elif os.path.isfile(resolved_pattern):
                search_dir = os.path.dirname(resolved_pattern)
                search_pattern = os.path.basename(resolved_pattern)
            else:
                # Assume it's a glob pattern
                search_dir = root_dir
                search_pattern = pattern
        else:
            search_dir = root_dir
            search_pattern = "**/*" if recursive else "*"

        matched_results: Dict[str, List[Tuple[int, str]]] = {}

        for current_root, dirs, files in os.walk(search_dir):
            for filename in files:
                if not fnmatch.fnmatch(filename, search_pattern):
                    continue

                file_path = os.path.join(current_root, filename)

                # Skip binary files
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, start=1):
                            if case_insensitive:
                                if word.lower() in line.lower():
                                    if file_path not in matched_results:
                                        matched_results[file_path] = []
                                    matched_results[file_path].append((line_num, line.strip()))
                except (UnicodeDecodeError, PermissionError):
                    continue  # Skip files that can't be read

        if not matched_results:
            return {
                "output": {},
                "error": "No matches found.",
                "error_code": "NO_MATCHES"
            }

        if len(matched_results) > 100:
            limited_results = dict(list(matched_results.items())[:100])
            return {
                "output": limited_results,
                "error": "Warning: More than 100 files matched. Showing first 100 results.",
                "error_code": "TOO_MANY_MATCHES"
            }

        return {
            "output": matched_results,
            "error": None,
            "error_code": "SUCCESS"
        }

    except ValueError as e:
        return {
            "output": None,
            "error": f"Invalid search parameters: {e}",
            "error_code": "INVALID_PARAMETERS"
        }
    except FileNotFoundError as e:
        return {
            "output": None,
            "error": f"No files found matching the pattern: {e}",
            "error_code": "NO_FILES_FOUND"
        }
    except PermissionError as e:
        return {
            "output": None,
            "error": f"Permission denied: {e}",
            "error_code": "PERMISSION_DENIED"
        }
    except IOError as e:
        return {
            "output": None,
            "error": f"Error reading files: {e}",
            "error_code": "IO_ERROR"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Unexpected error: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }