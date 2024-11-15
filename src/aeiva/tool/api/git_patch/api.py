# api.py

from typing import Dict, Any, List, Tuple, Optional
import os
from pathlib import Path


def git_patch(
    new_file_paths: List[str] = []
) -> Dict[str, Any]:
    """
    Generates a Git patch including specified new files.

    Args:
        new_file_paths (List[str], optional): Paths of the files newly created to be included in the patch.
                                               Defaults to an empty list.

    Returns:
        Dict[str, Any]: A dictionary containing 'patch', 'error', and 'error_code'.
    """
    try:
        # Determine the Git repository root
        git_root = find_git_root(os.getcwd())
        if not git_root:
            return {
                "patch": "",
                "error": "Not in a Git repository or its subdirectories.",
                "error_code": "NOT_A_GIT_REPO"
            }

        # Change to the Git root directory
        original_dir = os.getcwd()
        os.chdir(git_root)

        # Stage new files if any
        for file_path in new_file_paths:
            abs_file_path = os.path.abspath(file_path)
            if os.path.isfile(abs_file_path):
                add_command = f"git add {abs_file_path}"
                _, error = execute_command(add_command, cwd=git_root)
                if error:
                    os.chdir(original_dir)
                    return {
                        "patch": "",
                        "error": f"Error adding new file '{file_path}': {error}",
                        "error_code": "ADD_FILE_FAILED"
                    }
            else:
                os.chdir(original_dir)
                return {
                    "patch": "",
                    "error": f"New file path does not exist: {file_path}",
                    "error_code": "FILE_NOT_FOUND"
                }

        # Stage modified and deleted files
        stage_command = "git add -u"
        _, error = execute_command(stage_command, cwd=git_root)
        if error:
            os.chdir(original_dir)
            return {
                "patch": "",
                "error": f"Error staging changes: {error}",
                "error_code": "STAGE_FAILED"
            }

        # Generate the patch
        patch_command = "git diff --cached"
        patch_output, error = execute_command(patch_command, cwd=git_root)
        if error:
            os.chdir(original_dir)
            return {
                "patch": "",
                "error": f"Error generating patch: {error}",
                "error_code": "PATCH_GENERATION_FAILED"
            }

        # Revert staged changes to avoid altering the working directory
        revert_command = "git reset"
        execute_command(revert_command, cwd=git_root)

        # Change back to the original directory
        os.chdir(original_dir)

        if not patch_output.strip():
            return {
                "patch": "",
                "error": "No changes to include in the patch.",
                "error_code": "NO_CHANGES"
            }

        return {
            "patch": patch_output,
            "error": None,
            "error_code": "SUCCESS"
        }

    except Exception as e:
        return {
            "patch": "",
            "error": f"Unexpected error: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }


def find_git_root(path: str) -> Optional[str]:
    """
    Finds the root directory of the Git repository.

    Args:
        path (str): The starting directory path.

    Returns:
        Optional[str]: The Git repository root path or None if not found.
    """
    current = Path(path).resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").is_dir():
            return str(parent)
    return None


def execute_command(command: str, cwd: str = ".") -> Tuple[str, Optional[str]]:
    """
    Executes a shell command.

    Args:
        command (str): The command to execute.
        cwd (str): The working directory to execute the command in.

    Returns:
        Tuple[str, Optional[str]]: A tuple containing the command's stdout and stderr.
    """
    import subprocess

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip(), result.stderr.strip() if result.stderr else None
    except Exception as e:
        return "", str(e)