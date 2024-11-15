# test.py

import pytest
from unittest.mock import patch, mock_open
from .api import git_repo_tree, find_git_root, execute_command
import os


@pytest.mark.asyncio
async def test_git_repo_tree_success():
    git_repo_path = "/path/to/repo"
    tree_content = "file1.txt\nfile2.py\nsrc/main.py\n"

    with patch('os.path.isdir', side_effect=lambda x: True if x == os.path.join(git_repo_path, ".git") else False), \
         patch('execute_command', return_value=("", None)), \
         patch('builtins.open', mock_open(read_data=tree_content)), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.path.isfile', return_value=True):
        
        result = git_repo_tree(git_repo_path)
        assert result['success'] is True
        assert "Git repository tree has been generated successfully." in result['message']
        assert result['error_code'] == "SUCCESS"


@pytest.mark.asyncio
async def test_git_repo_tree_not_a_git_repo():
    git_repo_path = "/path/to/non_git_repo"

    with patch('os.path.isdir', return_value=False):
        result = git_repo_tree(git_repo_path)
        assert result['success'] is False
        assert result['message'] == f"The directory '{git_repo_path}' is not the root of a Git repository."
        assert result['error_code'] == "NOT_A_GIT_REPO"


@pytest.mark.asyncio
async def test_git_repo_tree_git_command_failed():
    git_repo_path = "/path/to/repo"

    with patch('os.path.isdir', side_effect=lambda x: True if x == os.path.join(git_repo_path, ".git") else False), \
         patch('execute_command', return_value=("", "Error executing Git command")):
        
        result = git_repo_tree(git_repo_path)
        assert result['success'] is False
        assert result['message'] == "Error executing Git command: Error executing Git command"
        assert result['error_code'] == "GIT_COMMAND_FAILED"


@pytest.mark.asyncio
async def test_git_repo_tree_file_creation_failed():
    git_repo_path = "/path/to/repo"

    with patch('os.path.isdir', side_effect=lambda x: True if x == os.path.join(git_repo_path, ".git") else False), \
         patch('execute_command', return_value=("", None)), \
         patch('os.path.isfile', return_value=False):
        
        result = git_repo_tree(git_repo_path)
        assert result['success'] is False
        assert result['message'] == "Error: Failed to create git_repo_tree.txt file."
        assert result['error_code'] == "FILE_CREATION_FAILED"


@pytest.mark.asyncio
async def test_git_repo_tree_file_read_error():
    git_repo_path = "/path/to/repo"

    with patch('os.path.isdir', side_effect=lambda x: True if x == os.path.join(git_repo_path, ".git") else False), \
         patch('execute_command', return_value=("", None)), \
         patch('os.path.isfile', return_value=True), \
         patch('builtins.open', mock_open()) as mock_file:
        
        mock_file.side_effect = IOError("Read error")
        result = git_repo_tree(git_repo_path)
        assert result['success'] is False
        assert result['message'] == "Error reading git_repo_tree.txt: Read error"
        assert result['error_code'] == "FILE_READ_ERROR"


@pytest.mark.asyncio
async def test_git_repo_tree_empty_tree():
    git_repo_path = "/path/to/repo"
    tree_content = "   "

    with patch('os.path.isdir', side_effect=lambda x: True if x == os.path.join(git_repo_path, ".git") else False), \
         patch('execute_command', return_value=("", None)), \
         patch('builtins.open', mock_open(read_data=tree_content)), \
         patch('os.path.isfile', return_value=True):
        
        result = git_repo_tree(git_repo_path)
        assert result['success'] is False
        assert result['message'] == "The repository tree is empty."
        assert result['error_code'] == "EMPTY_TREE"


@pytest.mark.asyncio
async def test_git_repo_tree_unexpected_error():
    with patch('os.path.isdir', side_effect=Exception("Unexpected exception")):
        result = git_repo_tree()
        assert result['success'] is False
        assert result['message'] == "Unexpected error: Unexpected exception"
        assert result['error_code'] == "UNEXPECTED_ERROR"