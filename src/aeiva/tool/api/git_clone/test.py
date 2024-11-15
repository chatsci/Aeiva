# test.py

import pytest
from unittest.mock import patch
from .api import git_clone, execute_command
import os


@pytest.mark.asyncio
async def test_git_clone_success_clone():
    repo_name = "composiohq/composio"
    destination = "/path/to/destination"
    commit_id = ""
    expected_output = "Cloning into '/path/to/destination/composio'...\nGit status output"

    with patch('os.path.exists', side_effect=lambda x: False), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('subprocess.run') as mock_run:
        
        mock_run.return_value.stdout = "Cloning into '/path/to/destination/composio'...\nGit status output"
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 0

        result = git_clone(repo_name, destination, just_reset=False, commit_id=commit_id)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"


@pytest.mark.asyncio
async def test_git_clone_success_reset():
    repo_name = "composiohq/composio"
    destination = "/path/to/existing_repo"
    just_reset = True
    commit_id = "abc123"
    expected_output = "Git reset output"

    with patch('os.path.isdir', return_value=True), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('subprocess.run') as mock_run:
        
        mock_run.return_value.stdout = "Git reset output"
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 0

        result = git_clone(repo_name, destination, just_reset=just_reset, commit_id=commit_id)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"


@pytest.mark.asyncio
async def test_git_clone_missing_repo_name():
    repo_name = "   "
    destination = "/path/to/destination"

    result = git_clone(repo_name, destination)
    assert result['output'] is None
    assert result['error'] == "Repository name must be provided."
    assert result['error_code'] == "MISSING_REPO_NAME"


@pytest.mark.asyncio
async def test_git_clone_missing_commit_id():
    repo_name = "composiohq/composio"
    destination = "/path/to/destination"
    just_reset = True
    commit_id = "   "

    result = git_clone(repo_name, destination, just_reset=just_reset, commit_id=commit_id)
    assert result['output'] is None
    assert result['error'] == "Commit ID must be provided when just_reset is True."
    assert result['error_code'] == "MISSING_COMMIT_ID"


@pytest.mark.asyncio
async def test_git_clone_not_a_git_repo():
    repo_name = "composiohq/composio"
    destination = "/path/to/existing_repo"
    just_reset = True
    commit_id = "abc123"

    with patch('os.path.isdir', return_value=False):
        result = git_clone(repo_name, destination, just_reset=just_reset, commit_id=commit_id)
        assert result['output'] is None
        assert result['error'] == f"The directory '{os.path.join(destination, 'composio')}' is not a git repository."
        assert result['error_code'] == "NOT_A_GIT_REPO"


@pytest.mark.asyncio
async def test_git_clone_destination_exists():
    repo_name = "composiohq/composio"
    destination = "/path/to/destination"
    with patch('os.path.exists', return_value=True):
        result = git_clone(repo_name, destination)
        assert result['output'] is None
        assert result['error'] == f"The directory '/path/to/destination/composio' already exists."
        assert result['error_code'] == "DESTINATION_EXISTS"


@pytest.mark.asyncio
async def test_git_clone_missing_github_token():
    repo_name = "composiohq/composio"
    destination = "/path/to/destination"
    with patch.dict(os.environ, {"GITHUB_ACCESS_TOKEN": ""}), \
         patch.dict(os.environ, {"ALLOW_CLONE_WITHOUT_REPO": "false"}):
        result = git_clone(repo_name, destination)
        assert result['output'] is None
        assert result['error'] == "Cannot clone GitHub repository without a GitHub access token."
        assert result['error_code'] == "MISSING_GITHUB_TOKEN"


@pytest.mark.asyncio
async def test_git_clone_git_command_failed():
    repo_name = "composiohq/composio"
    destination = "/path/to/destination"

    with patch('os.path.exists', side_effect=lambda x: False), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('subprocess.run') as mock_run:
        
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "Error cloning repository."
        mock_run.return_value.returncode = 1

        result = git_clone(repo_name, destination)
        assert result['output'] is None
        assert result['error'] == "Error cloning repository."
        assert result['error_code'] == "GIT_COMMAND_FAILED"


@pytest.mark.asyncio
async def test_git_clone_unexpected_error():
    repo_name = "composiohq/composio"
    destination = "/path/to/destination"

    with patch('os.path.exists', side_effect=Exception("Unexpected exception")):
        result = git_clone(repo_name, destination)
        assert result['output'] is None
        assert result['error'] == "Unexpected error: Unexpected exception"
        assert result['error_code'] == "UNEXPECTED_ERROR"