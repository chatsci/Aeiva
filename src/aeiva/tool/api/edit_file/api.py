# api.py

from typing import Dict, Any, Optional
import os

def edit_file(
    file_path: Optional[str],
    text: str,
    start_line: int,
    end_line: Optional[int] = None
) -> Dict[str, Any]:
    """
    Edits a file by replacing text in the specified line range.

    Args:
        file_path (Optional[str]): The path to the file to edit. If None, edits the currently open file.
        text (str): The text to replace in the specified line range.
        start_line (int): The starting line number (inclusive) for the edit.
        end_line (Optional[int]): The ending line number (inclusive) for the edit. If None, appends the text.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        # Determine the file to edit
        if file_path:
            resolved_path = os.path.abspath(os.path.expanduser(file_path))
        else:
            # Assume current open file is the current working directory's main file
            resolved_path = os.path.abspath(os.getcwd())  # Modify as needed

        if not os.path.isfile(resolved_path):
            return {
                "output": None,
                "error": f"File not found: {resolved_path}",
                "error_code": "FILE_NOT_FOUND"
            }

        with open(resolved_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_lines = len(lines)

        if start_line < 1 or (end_line is not None and end_line < start_line):
            return {
                "output": None,
                "error": "Invalid line range specified.",
                "error_code": "INVALID_LINE_RANGE"
            }

        # Adjust line numbers to zero-based index
        start_idx = start_line - 1
        end_idx = end_line if end_line else start_line

        if end_idx > total_lines:
            end_idx = total_lines

        # Replace the specified lines with the new text
        if end_line:
            replaced_text = ''.join(lines[start_idx:end_idx])
            lines[start_idx:end_idx] = [text + '\n']
        else:
            # Append the text
            replaced_text = ''
            lines.append(text + '\n')

        # Write back to the file
        with open(resolved_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return {
            "output": f"File edited successfully at {resolved_path}.",
            "error": None,
            "error_code": "SUCCESS"
        }

    except ValueError as e:
        return {
            "output": None,
            "error": f"Invalid parameters: {e}",
            "error_code": "INVALID_PARAMETERS"
        }
    except PermissionError as e:
        return {
            "output": None,
            "error": f"Permission denied: {e}",
            "error_code": "PERMISSION_DENIED"
        }
    except OSError as e:
        return {
            "output": None,
            "error": f"OS error occurred: {e}",
            "error_code": "OS_ERROR"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Unexpected error: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }