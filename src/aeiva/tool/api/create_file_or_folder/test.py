# test.py

import pytest
from unittest.mock import patch, mock_open
from .api import create_file_or_folder
import os

@pytest.mark.asyncio
async def test_create_file_success():
    path = "/path/to/new_file.txt"
    expected_output = f"File created at {os.path.abspath(path)}"

    with patch('os.path.exists', return_value=False), \
         patch('os.path.abspath', return_value=os.path.abspath(path)), \
         patch('os.path.expanduser', return_value=path), \
         patch('builtins.open', mock_open()) as mock_file:
        
        result = create_file_or_folder(path)
        mock_file.assert_called_once_with(os.path.abspath(path), 'w', encoding='utf-8')
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_create_directory_success():
    path = "/path/to/new_directory"
    expected_output = f"Directory created at {os.path.abspath(path)}"

    with patch('os.path.exists', return_value=False), \
         patch('os.path.abspath', return_value=os.path.abspath(path)), \
         patch('os.path.expanduser', return_value=path), \
         patch('os.makedirs') as mock_makedirs:
        
        result = create_file_or_folder(path, is_directory=True)
        mock_makedirs.assert_called_once_with(os.path.abspath(path), exist_ok=True)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_create_file_empty_path():
    path = "   "
    expected_error = "Path cannot be empty or just whitespace."
    expected_error_code = "EMPTY_PATH"

    result = create_file_or_folder(path)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "EMPTY_PATH"

@pytest.mark.asyncio
async def test_create_directory_already_exists():
    path = "/path/to/existing_directory"
    expected_error = f"Directory already exists: {os.path.abspath(path)}"
    expected_error_code = "DIRECTORY_EXISTS"

    with patch('os.path.exists', return_value=True), \
         patch('os.path.abspath', return_value=os.path.abspath(path)), \
         patch('os.path.expanduser', return_value=path):
        
        result = create_file_or_folder(path, is_directory=True)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "DIRECTORY_EXISTS"

@pytest.mark.asyncio
async def test_create_file_already_exists():
    path = "/path/to/existing_file.txt"
    expected_error = f"File already exists: {os.path.abspath(path)}"
    expected_error_code = "FILE_EXISTS"

    with patch('os.path.exists', return_value=True), \
         patch('os.path.abspath', return_value=os.path.abspath(path)), \
         patch('os.path.expanduser', return_value=path):
        
        result = create_file_or_folder(path)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "FILE_EXISTS"

@pytest.mark.asyncio
async def test_create_file_permission_denied():
    path = "/protected/path/new_file.txt"
    expected_error_code = "PERMISSION_DENIED"
    expected_error_message = f"Permission denied while creating directories: [Errno 13] Permission denied: '/protected/path'"

    with patch('os.path.exists', return_value=False), \
         patch('os.path.abspath', return_value=os.path.abspath(path)), \
         patch('os.path.expanduser', return_value=path), \
         patch('os.makedirs', side_effect=PermissionError("Permission denied")):
        
        result = create_file_or_folder(path)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "PERMISSION_DENIED"

@pytest.mark.asyncio
async def test_create_file_os_error():
    path = "/path/to/file.txt"
    expected_error_code = "OS_ERROR"
    expected_error_message = f"OS error occurred: [Errno 22] Invalid argument: '{path}'"

    with patch('os.path.exists', return_value=False), \
         patch('os.path.abspath', return_value=os.path.abspath(path)), \
         patch('os.path.expanduser', return_value=path), \
         patch('builtins.open', mock_open()) as mock_file:
        
        mock_file.side_effect = OSError("[Errno 22] Invalid argument")
        result = create_file_or_folder(path)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "OS_ERROR"

@pytest.mark.asyncio
async def test_create_file_unexpected_error():
    path = "/path/to/file.txt"
    expected_error_code = "UNEXPECTED_ERROR"
    expected_error_message = f"Unexpected error: Unexpected exception"

    with patch('os.path.exists', return_value=False), \
         patch('os.path.abspath', return_value=os.path.abspath(path)), \
         patch('os.path.expanduser', return_value=path), \
         patch('os.makedirs', side_effect=Exception("Unexpected exception")):
        
        result = create_file_or_folder(path)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "UNEXPECTED_ERROR"