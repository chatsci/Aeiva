# api.py

from typing import Dict, Any, Optional, Tuple
import os
from pathlib import Path


def git_repo_tree(
    git_repo_path: str = "."
) -> Dict[str, Any]:
    """
    Creates a tree representation of the Git repository.

    This action generates a text file containing the tree structure of the
    current Git repository. It lists all files tracked by Git in the repository.

    Args:
        git_repo_path (str, optional): Relative path to the Git repository.
                                       Defaults to the current directory.

    Returns:
        Dict[str, Any]: A dictionary containing 'success', 'message', and 'error_code'.
    """
    try:
        # Resolve the repository path
        repo_path = os.path.abspath(os.path.expanduser(git_repo_path))

        # Check if the path is a Git repository
        if not os.path.isdir(os.path.join(repo_path, ".git")):
            return {
                "success": False,
                "message": f"The directory '{repo_path}' is not the root of a Git repository.",
                "error_code": "NOT_A_GIT_REPO"
            }

        # Construct the Git tree command
        tree_file = os.path.join(repo_path, "git_repo_tree.txt")
        command = f"git -C {repo_path} ls-tree -r HEAD --name-only > {tree_file}"

        # Execute the command
        output, error = execute_command(command, cwd=repo_path)

        if error:
            return {
                "success": False,
                "message": f"Error executing Git command: {error}",
                "error_code": "GIT_COMMAND_FAILED"
            }

        # Verify that the tree file was created
        if not os.path.isfile(tree_file):
            return {
                "success": False,
                "message": "Error: Failed to create git_repo_tree.txt file.",
                "error_code": "FILE_CREATION_FAILED"
            }

        # Optionally, read the tree content
        try:
            with open(tree_file, "r", encoding="utf-8") as f:
                tree_content = f.read()
        except IOError as e:
            return {
                "success": False,
                "message": f"Error reading git_repo_tree.txt: {e}",
                "error_code": "FILE_READ_ERROR"
            }

        if not tree_content.strip():
            return {
                "success": False,
                "message": "The repository tree is empty.",
                "error_code": "EMPTY_TREE"
            }

        return {
            "success": True,
            "message": (
                "Git repository tree has been generated successfully. "
                "Check git_repo_tree.txt in the repository root for the results."
            ),
            "error_code": "SUCCESS"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected error: {e}",
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