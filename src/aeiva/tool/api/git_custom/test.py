# test.py

import pytest
from unittest.mock import patch
from .api import git_custom
import os


@pytest.mark.asyncio
async def test_git_custom_success():
    cmd = "status"
    cwd = "/path/to/repo"
    expected_output = "On branch main\nYour branch is up to date with 'origin/main'.\n\nnothing to commit, working tree clean"

    with patch('os.path.isdir', return_value=True), \
         patch('os.path.join', return_value=os.path.join(cwd, ".git")), \
         patch('subprocess.run') as mock_run:
        
        mock_run.return_value.stdout = expected_output
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 0

        result = git_custom(cmd, cwd=cwd)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"


@pytest.mark.asyncio
async def test_git_custom_missing_command():
    cmd = "   "
    result = git_custom(cmd)
    assert result['output'] is None
    assert result['error'] == "Git command must be provided."
    assert result['error_code'] == "MISSING_COMMAND"


@pytest.mark.asyncio
async def test_git_custom_not_a_git_repo():
    cmd = "status"
    cwd = "/path/to/non_git_directory"

    with patch('os.path.isdir', return_value=False):
        result = git_custom(cmd, cwd=cwd)
        assert result['output'] is None
        assert result['error'] == f"The directory '{cwd}' is not a Git repository."
        assert result['error_code'] == "NOT_A_GIT_REPO"


@pytest.mark.asyncio
async def test_git_custom_git_command_failed():
    cmd = "invalid_command"
    cwd = "/path/to/repo"
    expected_error = "fatal: ambiguous argument 'invalid_command': unknown revision or path not in the working tree."

    with patch('os.path.isdir', return_value=True), \
         patch('os.path.join', return_value=os.path.join(cwd, ".git")), \
         patch('subprocess.run') as mock_run:
        
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = expected_error
        mock_run.return_value.returncode = 1

        result = git_custom(cmd, cwd=cwd)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "GIT_COMMAND_FAILED"


@pytest.mark.asyncio
async def test_git_custom_unexpected_error():
    cmd = "status"
    cwd = "/path/to/repo"

    with patch('os.path.isdir', return_value=True), \
         patch('os.path.join', return_value=os.path.join(cwd, ".git")), \
         patch('subprocess.run', side_effect=Exception("Unexpected exception")):
        
        result = git_custom(cmd, cwd=cwd)
        assert result['output'] is None
        assert result['error'] == "Unexpected error: Unexpected exception"
        assert result['error_code'] == "UNEXPECTED_ERROR"