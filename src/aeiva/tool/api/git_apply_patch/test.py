# test.py

import pytest
from unittest.mock import patch, mock_open
from .api import git_apply_patch
import os


@pytest.mark.asyncio
async def test_git_apply_patch_success():
    patch_content = "diff --git a/file1.txt b/file1.txt\nindex e69de29..0c1e5c1 100644\n--- a/file1.txt\n+++ b/file1.txt\n@@ -0,0 +1 @@\n+Hello World\n"
    git_root = "/path/to/repo"
    with patch('os.getcwd', return_value=git_root), \
         patch('pathlib.Path.is_dir', side_effect=lambda x: True if x == os.path.join(git_root, ".git") else False), \
         patch('execute_command', side_effect=[
             ("", None),  # Write patch file
             ("", None),  # Apply patch
             ("", None)   # Revert
         ]), \
         patch('builtins.open', mock_open()), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.remove') as mock_remove:
        
        result = git_apply_patch(patch_content)
        assert result['message'] == "Successfully applied patch, lint checks passed."
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"
        mock_remove.assert_called_once_with(os.path.join(git_root, "temp_patch.patch"))


@pytest.mark.asyncio
async def test_git_apply_patch_missing_patch():
    patch_content = "   "
    result = git_apply_patch(patch_content)
    assert result['message'] == ""
    assert result['error'] == "Patch content must be provided."
    assert result['error_code'] == "MISSING_PATCH"


@pytest.mark.asyncio
async def test_git_apply_patch_not_a_git_repo():
    with patch('os.getcwd', return_value="/path/to/non_git_dir"), \
         patch('pathlib.Path.is_dir', return_value=False):
        
        result = git_apply_patch("diff --git a/file1.txt b/file1.txt\n")
        assert result['message'] == ""
        assert result['error'] == "Not in a Git repository or its subdirectories."
        assert result['error_code'] == "NOT_A_GIT_REPO"


@pytest.mark.asyncio
async def test_git_apply_patch_apply_failed():
    patch_content = "invalid patch content"
    git_root = "/path/to/repo"

    with patch('os.getcwd', return_value=git_root), \
         patch('pathlib.Path.is_dir', side_effect=lambda x: True if x == os.path.join(git_root, ".git") else False), \
         patch('execute_command', side_effect=[
             ("", None),  # Write patch file
             ("", "Error applying patch"),  # Apply patch
             ("", None)   # Revert
         ]), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x):
        
        result = git_apply_patch(patch_content)
        assert result['message'] == ""
        assert result['error'] == "No Update, found error during applying patch: Error applying patch"
        assert result['error_code'] == "APPLY_PATCH_FAILED"


@pytest.mark.asyncio
async def test_git_apply_patch_lint_errors():
    patch_content = "diff --git a/file1.py b/file1.py\nindex e69de29..0c1e5c1 100644\n--- a/file1.py\n+++ b/file1.py\n@@ -0,0 +1 @@\n+print('Hello World')\n"
    git_root = "/path/to/repo"
    lint_errors = "file1.py:1:1: F401 'os' imported but unused"

    with patch('os.getcwd', return_value=git_root), \
         patch('pathlib.Path.is_dir', side_effect=lambda x: True if x == os.path.join(git_root, ".git") else False), \
         patch('execute_command', side_effect=[
             ("", None),  # Write patch file
             ("", None),  # Apply patch
             (lint_errors, None),  # Lint checks
             ("", None)   # Revert
         ]), \
         patch('builtins.open', mock_open(read_data=lint_errors)), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.remove') as mock_remove:
        
        result = git_apply_patch(patch_content)
        assert result['message'] == ""
        assert result['error'] == f"No Update, found lint errors after applying patch: {lint_errors}"
        assert result['error_code'] == "LINT_ERRORS"
        mock_remove.assert_called_once_with(os.path.join(git_root, "temp_patch.patch"))


@pytest.mark.asyncio
async def test_git_apply_patch_file_not_found():
    patch_content = "diff --git a/nonexistent_file.txt b/nonexistent_file.txt\n"
    git_root = "/path/to/repo"

    with patch('os.getcwd', return_value=git_root), \
         patch('pathlib.Path.is_dir', side_effect=lambda x: True if x == os.path.join(git_root, ".git") else False), \
         patch('execute_command', side_effect=[
             ("", None),  # Write patch file
             ("", None),  # Apply patch
             ("", None),  # Lint checks
             ("", None)   # Revert
         ]), \
         patch('get_files_from_patch', return_value=["nonexistent_file.txt"]), \
         patch('run_lint_checks', return_value=None), \
         patch('builtins.open', mock_open()), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.remove') as mock_remove:
        
        # Simulate git apply failing due to file not found
        with patch('execute_command', side_effect=[("", None), ("", "error: patch failed: nonexistent_file.txt")]):
            result = git_apply_patch(patch_content)
            assert result['message'] == ""
            assert result['error'] == "No Update, found error during applying patch: error: patch failed: nonexistent_file.txt"
            assert result['error_code'] == "APPLY_PATCH_FAILED"
            mock_remove.assert_called_once_with(os.path.join(git_root, "temp_patch.patch"))


@pytest.mark.asyncio
async def test_git_apply_patch_unexpected_error():
    with patch('os.getcwd', side_effect=Exception("Unexpected exception")):
        result = git_apply_patch("diff --git a/file1.txt b/file1.txt\n")
        assert result['message'] == ""
        assert result['error'] == "Unexpected error: Unexpected exception"
        assert result['error_code'] == "UNEXPECTED_ERROR"