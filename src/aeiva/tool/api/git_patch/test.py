# test.py

import pytest
from unittest.mock import patch
from .api import git_patch, find_git_root, execute_command
import os


@pytest.mark.asyncio
async def test_git_patch_success_no_new_files():
    patch_content = "diff --git a/file1.txt b/file1.txt\nindex e69de29..0c1e5c1 100644\n--- a/file1.txt\n+++ b/file1.txt\n@@ -0,0 +1 @@\n+Hello World\n"
    with patch('os.getcwd', return_value="/path/to/repo"), \
         patch('pathlib.Path.is_dir', side_effect=lambda x: True if x == "/path/to/repo/.git" else False), \
         patch('execute_command', return_value=(patch_content, None)), \
         patch('os.chdir') as mock_chdir:
        
        result = git_patch()
        assert result['patch'] == patch_content
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"
        mock_chdir.assert_any_call("/path/to/repo")


@pytest.mark.asyncio
async def test_git_patch_success_with_new_files():
    new_file_paths = ["new_file1.txt", "new_file2.py"]
    patch_content = "diff --git a/new_file1.txt b/new_file1.txt\nnew file mode 100644\nindex 0000000..e69de29\n--- /dev/null\n+++ b/new_file1.txt\n@@ -0,0 +1 @@\n+New file content\n\ndiff --git a/new_file2.py b/new_file2.py\nnew file mode 100644\nindex 0000000..e69de29\n--- /dev/null\n+++ b/new_file2.py\n@@ -0,0 +1 @@\n+# New Python file\n"
    with patch('os.getcwd', return_value="/path/to/repo"), \
         patch('pathlib.Path.is_dir', side_effect=lambda x: True if x == "/path/to/repo/.git" else False), \
         patch('execute_command', return_value=(patch_content, None)), \
         patch('os.path.isfile', side_effect=lambda x: True), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.chdir') as mock_chdir:
        
        result = git_patch(new_file_paths=new_file_paths)
        assert result['patch'] == patch_content
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"
        mock_chdir.assert_any_call("/path/to/repo")


@pytest.mark.asyncio
async def test_git_patch_not_a_git_repo():
    with patch('os.getcwd', return_value="/path/to/non_git_dir"), \
         patch('pathlib.Path.is_dir', return_value=False):
        
        result = git_patch()
        assert result['patch'] == ""
        assert result['error'] == "Not in a Git repository or its subdirectories."
        assert result['error_code'] == "NOT_A_GIT_REPO"


@pytest.mark.asyncio
async def test_git_patch_add_file_failed():
    new_file_paths = ["new_file1.txt"]
    with patch('os.getcwd', return_value="/path/to/repo"), \
         patch('pathlib.Path.is_dir', side_effect=lambda x: True if x == "/path/to/repo/.git" else False), \
         patch('execute_command', side_effect=[("", "Error adding file.")]), \
         patch('os.path.isfile', return_value=True), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.chdir') as mock_chdir:
        
        result = git_patch(new_file_paths=new_file_paths)
        assert result['patch'] == ""
        assert result['error'] == "Error adding new file 'new_file1.txt': Error adding file."
        assert result['error_code'] == "ADD_FILE_FAILED"
        mock_chdir.assert_any_call("/path/to/repo")


@pytest.mark.asyncio
async def test_git_patch_file_not_found():
    new_file_paths = ["nonexistent_file.txt"]
    with patch('os.getcwd', return_value="/path/to/repo"), \
         patch('pathlib.Path.is_dir', side_effect=lambda x: True if x == "/path/to/repo/.git" else False), \
         patch('execute_command', return_value=("", None)), \
         patch('os.path.isfile', return_value=False), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.chdir') as mock_chdir:
        
        result = git_patch(new_file_paths=new_file_paths)
        assert result['patch'] == ""
        assert result['error'] == "New file path does not exist: nonexistent_file.txt"
        assert result['error_code'] == "FILE_NOT_FOUND"
        mock_chdir.assert_any_call("/path/to/repo")


@pytest.mark.asyncio
async def test_git_patch_stage_failed():
    with patch('os.getcwd', return_value="/path/to/repo"), \
         patch('pathlib.Path.is_dir', side_effect=lambda x: True if x == "/path/to/repo/.git" else False), \
         patch('execute_command', side_effect=[("", None), ("", "Error staging changes.")]), \
         patch('os.path.isfile', return_value=False), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.chdir') as mock_chdir:
        
        result = git_patch()
        assert result['patch'] == ""
        assert result['error'] == "Error staging changes: Error staging changes."
        assert result['error_code'] == "STAGE_FAILED"
        mock_chdir.assert_any_call("/path/to/repo")


@pytest.mark.asyncio
async def test_git_patch_patch_generation_failed():
    with patch('os.getcwd', return_value="/path/to/repo"), \
         patch('pathlib.Path.is_dir', side_effect=lambda x: True if x == "/path/to/repo/.git" else False), \
         patch('execute_command', side_effect=[("diff content", None), ("", "Error generating patch.")]), \
         patch('os.path.isfile', return_value=False), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.chdir') as mock_chdir:
        
        result = git_patch()
        assert result['patch'] == ""
        assert result['error'] == "Error generating patch: Error generating patch."
        assert result['error_code'] == "PATCH_GENERATION_FAILED"
        mock_chdir.assert_any_call("/path/to/repo")


@pytest.mark.asyncio
async def test_git_patch_no_changes():
    with patch('os.getcwd', return_value="/path/to/repo"), \
         patch('pathlib.Path.is_dir', return_value=True), \
         patch('execute_command', return_value=("", None)), \
         patch('os.chdir') as mock_chdir:
        
        result = git_patch()
        assert result['patch'] == ""
        assert result['error'] == "No changes to include in the patch."
        assert result['error_code'] == "NO_CHANGES"
        mock_chdir.assert_any_call("/path/to/repo")


@pytest.mark.asyncio
async def test_git_patch_unexpected_error():
    with patch('os.getcwd', side_effect=Exception("Unexpected exception")):
        result = git_patch()
        assert result['patch'] == ""
        assert result['error'] == "Unexpected error: Unexpected exception"
        assert result['error_code'] == "UNEXPECTED_ERROR"