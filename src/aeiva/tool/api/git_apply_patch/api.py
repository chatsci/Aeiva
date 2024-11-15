# api.py

from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
import os


def git_apply_patch(
    patch: str
) -> Dict[str, Any]:
    """
    Applies a Git patch to the current repository and performs lint checks.

    Args:
        patch (str): The patch to apply in the format of a proper diff.

    Returns:
        Dict[str, Any]: A dictionary containing 'message', 'error', and 'error_code'.
    """
    try:
        if not patch.strip():
            return {
                "message": "",
                "error": "Patch content must be provided.",
                "error_code": "MISSING_PATCH"
            }

        # Determine the Git repository root
        git_root = find_git_root(os.getcwd())
        if not git_root:
            return {
                "message": "",
                "error": "Not in a Git repository or its subdirectories.",
                "error_code": "NOT_A_GIT_REPO"
            }

        # Path to temporary patch file
        patch_file = os.path.join(git_root, "temp_patch.patch")

        # Write the patch content to the patch file
        with open(patch_file, "w", encoding="utf-8") as f:
            f.write(patch)

        # Apply the patch
        apply_command = f"git apply --verbose {patch_file}"
        output, error = execute_command(apply_command, cwd=git_root)

        if error:
            os.remove(patch_file)
            return {
                "message": "",
                "error": f"No Update, found error during applying patch: {error}",
                "error_code": "APPLY_PATCH_FAILED"
            }

        # Perform lint checks on affected files
        affected_files = get_files_from_patch(patch)
        lint_errors_before = run_lint_checks(affected_files, git_root)

        if lint_errors_before:
            # Revert changes if lint errors are introduced
            revert_command = "git reset --hard"
            execute_command(revert_command, cwd=git_root)
            os.remove(patch_file)
            return {
                "message": "",
                "error": f"No Update, found lint errors after applying patch: {lint_errors_before}",
                "error_code": "LINT_ERRORS"
            }

        # Clean up the temporary patch file
        os.remove(patch_file)

        return {
            "message": "Successfully applied patch, lint checks passed.",
            "error": None,
            "error_code": "SUCCESS"
        }

    except FileNotFoundError as e:
        return {
            "message": "",
            "error": f"File not found: {e}",
            "error_code": "FILE_NOT_FOUND"
        }
    except PermissionError as e:
        return {
            "message": "",
            "error": f"Permission denied: {e}",
            "error_code": "PERMISSION_DENIED"
        }
    except OSError as e:
        return {
            "message": "",
            "error": f"OS error occurred: {e}",
            "error_code": "OS_ERROR"
        }
    except Exception as e:
        return {
            "message": "",
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


def get_files_from_patch(patch_content: str) -> List[str]:
    """
    Extracts the list of files that will be modified by the patch.

    Args:
        patch_content (str): The content of the patch.

    Returns:
        List[str]: A list of file paths to be modified.
    """
    files = []
    for line in patch_content.splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            file_path = line.split()[1]
            if file_path != "/dev/null":
                # Remove 'a/' or 'b/' prefix if present
                if file_path.startswith(("a/", "b/")):
                    file_path = file_path[2:]
                files.append(file_path)
    return list(set(files))


def run_lint_checks(files: List[str], git_root: str) -> Optional[str]:
    """
    Runs lint checks on the specified files.

    Args:
        files (List[str]): The list of file paths to lint.
        git_root (str): The root directory of the Git repository.

    Returns:
        Optional[str]: A string of lint errors if any, else None.
    """
    import subprocess

    lint_errors = ""
    for file in files:
        file_path = os.path.join(git_root, file)
        if file.endswith(".py"):
            lint_command = f"flake8 {file_path}"
            output, error = execute_command(lint_command, cwd=git_root)
            if error:
                lint_errors += f"Error linting '{file}': {error}\n"
            if output:
                lint_errors += f"Lint issues in '{file}':\n{output}\n"

    return lint_errors if lint_errors else None