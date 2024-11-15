# tools/find_file/api.py

from typing import Dict, Any, List, Optional
import os
import fnmatch

def find_file(
    pattern: str,
    depth: Optional[int] = None,
    case_sensitive: bool = False,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Finds files matching a pattern within a directory structure.

    Args:
        pattern (str): Pattern to search for (supports wildcards, e.g., "*.txt").
        depth (Optional[int]): Maximum depth to search. None for unlimited.
        case_sensitive (bool): If True, the search is case-sensitive.
        include (Optional[List[str]]): List of directories to include in the search.
        exclude (Optional[List[str]]): List of directories to exclude from the search.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not pattern:
            return {
                "output": None,
                "error": "Pattern must be provided.",
                "error_code": "MISSING_PATTERN"
            }

        # Determine the root directory
        root_dir = os.getcwd()

        # Prepare include and exclude directories
        include_dirs = set(include) if include else {root_dir}
        exclude_dirs = set(exclude) if exclude else set()

        matched_files = []

        for current_root, dirs, files in os.walk(root_dir):
            # Calculate current depth
            current_depth = current_root[len(root_dir):].count(os.sep)
            if depth is not None and current_depth > depth:
                # Prevent walking deeper
                dirs[:] = []
                continue

            # Modify dirs in-place to exclude directories
            dirs[:] = [d for d in dirs if os.path.join(current_root, d) not in exclude_dirs]

            # Check if current directory is in include_dirs
            if include_dirs and not any(os.path.commonpath([inc_dir, current_root]) == inc_dir for inc_dir in include_dirs):
                continue

            for filename in files:
                # Handle case sensitivity
                if not case_sensitive:
                    if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                        matched_files.append(os.path.join(current_root, filename))
                else:
                    if fnmatch.fnmatch(filename, pattern):
                        matched_files.append(os.path.join(current_root, filename))

        if not matched_files:
            return {
                "output": None,
                "error": "No files found matching the pattern.",
                "error_code": "NO_MATCHES"
            }

        if len(matched_files) > 200:
            return {
                "output": matched_files[:200],
                "error": f"Too many results found ({len(matched_files)}). Showing first 200 results.",
                "error_code": "TOO_MANY_RESULTS"
            }

        return {
            "output": matched_files,
            "error": None,
            "error_code": "SUCCESS"
        }

    except Exception as e:
        return {
            "output": None,
            "error": f"Error finding files: {e}",
            "error_code": "FIND_FILE_FAILED"
        }