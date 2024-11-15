# api.py

from typing import Dict, Any, Optional, Tuple
import os


def git_clone(
    repo_name: str,
    destination: Optional[str] = None,
    just_reset: bool = False,
    commit_id: str = ""
) -> Dict[str, Any]:
    """
    Clones a Git repository or resets an existing repository to a specific commit.

    Args:
        repo_name (str): The Git repository to clone in the format "owner/repo".
        destination (Optional[str]): The local directory to clone the repository into.
                                     Defaults to the current working directory.
        just_reset (bool): If True, resets the existing repository to the specified commit.
                           Defaults to False.
        commit_id (str): The commit ID to reset to. If empty, clones the default branch.
                         Required if just_reset is True.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not repo_name.strip():
            return {
                "output": None,
                "error": "Repository name must be provided.",
                "error_code": "MISSING_REPO_NAME"
            }

        if just_reset and not commit_id.strip():
            return {
                "output": None,
                "error": "Commit ID must be provided when just_reset is True.",
                "error_code": "MISSING_COMMIT_ID"
            }

        # Determine the root directory
        root_dir = os.getcwd()

        # Prepare destination directory
        if destination:
            dest_path = os.path.abspath(os.path.expanduser(destination))
        else:
            dest_path = root_dir

        repo_dir_name = repo_name.split("/")[-1]
        repo_path = os.path.join(dest_path, repo_dir_name)

        if just_reset:
            if not os.path.isdir(os.path.join(repo_path, ".git")):
                return {
                    "output": None,
                    "error": f"The directory '{repo_path}' is not a git repository.",
                    "error_code": "NOT_A_GIT_REPO"
                }

            # Construct git reset command
            reset_commands = [
                "git remote get-url origin",
                f"git fetch --depth 1 origin {commit_id}",
                f"git reset --hard {commit_id}",
                "git clean -fdx",
                "git status"
            ]
            command = " && ".join(reset_commands)

        else:
            if os.path.exists(repo_path):
                return {
                    "output": None,
                    "error": f"The directory '{repo_path}' already exists.",
                    "error_code": "DESTINATION_EXISTS"
                }

            github_access_token = os.environ.get("GITHUB_ACCESS_TOKEN", "").strip()

            if not github_access_token and os.environ.get("ALLOW_CLONE_WITHOUT_REPO") != "true":
                return {
                    "output": None,
                    "error": "Cannot clone GitHub repository without a GitHub access token.",
                    "error_code": "MISSING_GITHUB_TOKEN"
                }

            clone_url = f"https://{github_access_token + '@' if github_access_token else ''}github.com/{repo_name}.git"

            if commit_id:
                clone_commands = [
                    f"git clone --depth 1 {clone_url} -q",
                    f"cd {repo_dir_name}",
                    f"git fetch --depth 1 origin {commit_id}",
                    f"git checkout {commit_id}",
                    "git status"
                ]
            else:
                clone_commands = [
                    f"git clone --depth 1 {clone_url} -q",
                    f"cd {repo_dir_name}",
                    "git status"
                ]
            command = " && ".join(clone_commands)

        # Execute the command
        output, error = execute_command(command, cwd=dest_path)

        if error:
            return {
                "output": None,
                "error": error,
                "error_code": "GIT_COMMAND_FAILED"
            }

        return {
            "output": output,
            "error": None,
            "error_code": "SUCCESS"
        }

    except RuntimeError as e:
        return {
            "output": None,
            "error": str(e),
            "error_code": "RUNTIME_ERROR"
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