# test.py

import pytest
from unittest.mock import patch
from .api import rename_file
import os

@pytest.mark.asyncio
async def test_rename_file_success():
    old_file_path = "/path/to/old_file.txt"
    new_file_path = "/path/to/new_file.txt"
    expected_output = f"File renamed from {os.path.abspath(old_file_path)} to {os.path.abspath(new_file_path)}"

    with patch('os.path.exists', side_effect=lambda x: False if x == os.path.abspath(new_file_path) else True), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.makedirs') as mock_makedirs, \
         patch('os.rename') as mock_rename:
        
        result = rename_file(old_file_path, new_file_path)
        mock_makedirs.assert_not_called()
        mock_rename.assert_called_once_with(os.path.abspath(old_file_path), os.path.abspath(new_file_path))
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_rename_file_missing_paths():
    old_file_path = "   "
    new_file_path = ""
    expected_error = "Both old_file_path and new_file_path must be provided."
    expected_error_code = "MISSING_PATHS"

    result = rename_file(old_file_path, new_file_path)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "MISSING_PATHS"

@pytest.mark.asyncio
async def test_rename_file_source_not_found():
    old_file_path = "/path/to/nonexistent_file.txt"
    new_file_path = "/path/to/new_file.txt"
    expected_error = f"File not found: {os.path.abspath(old_file_path)}"
    expected_error_code = "FILE_NOT_FOUND"

    with patch('os.path.exists', return_value=False), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x):
        
        result = rename_file(old_file_path, new_file_path)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "FILE_NOT_FOUND"

@pytest.mark.asyncio
async def test_rename_file_destination_exists():
    old_file_path = "/path/to/old_file.txt"
    new_file_path = "/path/to/existing_file.txt"
    expected_error = f"Destination already exists: {os.path.abspath(new_file_path)}"
    expected_error_code = "DESTINATION_EXISTS"

    with patch('os.path.exists', return_value=True), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x):
        
        result = rename_file(old_file_path, new_file_path)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "DESTINATION_EXISTS"

@pytest.mark.asyncio
async def test_rename_file_permission_denied():
    old_file_path = "/protected/path/old_file.txt"
    new_file_path = "/protected/path/new_file.txt"
    expected_error = f"Permission denied: [Errno 13] Permission denied: '{os.path.abspath(new_file_path)}'"
    expected_error_code = "PERMISSION_DENIED"

    with patch('os.path.exists', return_value=False), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.makedirs', side_effect=PermissionError("Permission denied")):
        
        result = rename_file(old_file_path, new_file_path)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "PERMISSION_DENIED"

@pytest.mark.asyncio
async def test_rename_file_os_error():
    old_file_path = "/path/to/old_file.txt"
    new_file_path = "/path/to/new_file.txt"
    expected_error = f"OS error occurred: [Errno 22] Invalid argument: '{os.path.abspath(new_file_path)}'"
    expected_error_code = "OS_ERROR"

    with patch('os.path.exists', return_value=False), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.makedirs') as mock_makedirs, \
         patch('os.rename', side_effect=OSError("[Errno 22] Invalid argument")):
        
        result = rename_file(old_file_path, new_file_path)
        mock_makedirs.assert_called_once_with(os.path.dirname(os.path.abspath(new_file_path)), exist_ok=True)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "OS_ERROR"

@pytest.mark.asyncio
async def test_rename_file_unexpected_error():
    old_file_path = "/path/to/old_file.txt"
    new_file_path = "/path/to/new_file.txt"
    expected_error = f"Unexpected error: Unexpected exception"
    expected_error_code = "UNEXPECTED_ERROR"

    with patch('os.path.exists', return_value=False), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.makedirs', side_effect=Exception("Unexpected exception")):
        
        result = rename_file(old_file_path, new_file_path)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "UNEXPECTED_ERROR"