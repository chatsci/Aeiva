# api.py

from typing import Dict, Any, Optional, Tuple
import os


def git_custom(
    cmd: str,
    cwd: Optional[str] = None
) -> Dict[str, Any]:
    """
    Runs a custom Git command in the specified directory.

    Args:
        cmd (str): The custom Git command to run. Do not include the 'git' prefix.
                   Example: 'add -u', 'commit -m "test-commit"'.
        cwd (Optional[str]): The directory to run the Git command in. Defaults to the current working directory.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not cmd.strip():
            return {
                "output": None,
                "error": "Git command must be provided.",
                "error_code": "MISSING_COMMAND"
            }

        # Resolve the working directory
        if cwd:
            working_dir = os.path.abspath(os.path.expanduser(cwd))
        else:
            working_dir = os.getcwd()

        # Check if the directory is a Git repository
        if not os.path.isdir(os.path.join(working_dir, ".git")):
            return {
                "output": None,
                "error": f"The directory '{working_dir}' is not a Git repository.",
                "error_code": "NOT_A_GIT_REPO"
            }

        # Construct the full Git command
        full_cmd = f"git {cmd}"

        # Execute the command
        output, error = execute_command(full_cmd, cwd=working_dir)

        if error:
            return {
                "output": None,
                "error": error,
                "error_code": "GIT_COMMAND_FAILED"
            }

        return {
            "output": output if output else "Git command executed successfully.",
            "error": None,
            "error_code": "SUCCESS"
        }

    except Exception as e:
        return {
            "output": None,
            "error": f"Unexpected error: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }


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