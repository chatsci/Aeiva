# test.py

import pytest
from unittest.mock import patch, mock_open
from .api import edit_file
import os

@pytest.mark.asyncio
async def test_edit_file_success_replace():
    file_path = "/path/to/file.txt"
    text = "New content"
    start_line = 2
    end_line = 4
    expected_output = f"File edited successfully at {os.path.abspath(file_path)}"

    original_content = ["Line 1\n", "Line 2\n", "Line 3\n", "Line 4\n", "Line 5\n"]
    updated_content = ["Line 1\n", "New content\n", "Line 5\n"]

    m = mock_open(read_data=''.join(original_content))
    with patch('os.path.isfile', return_value=True), \
         patch('os.path.abspath', return_value=os.path.abspath(file_path)), \
         patch('os.path.expanduser', return_value=file_path), \
         patch('builtins.open', m):
        
        # Mock write
        handle = m()
        handle.writelines = mock_open().return_value.writelines

        result = edit_file(file_path, text, start_line, end_line)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_edit_file_success_append():
    file_path = "/path/to/file.txt"
    text = "Appended line"
    start_line = 6
    end_line = None
    expected_output = f"File edited successfully at {os.path.abspath(file_path)}"

    original_content = ["Line 1\n", "Line 2\n", "Line 3\n", "Line 4\n", "Line 5\n"]
    updated_content = original_content + ["Appended line\n"]

    m = mock_open(read_data=''.join(original_content))
    with patch('os.path.isfile', return_value=True), \
         patch('os.path.abspath', return_value=os.path.abspath(file_path)), \
         patch('os.path.expanduser', return_value=file_path), \
         patch('builtins.open', m):
        
        handle = m()
        handle.writelines = mock_open().return_value.writelines

        result = edit_file(file_path, text, start_line, end_line)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_edit_file_file_not_found():
    file_path = "/path/to/nonexistent_file.txt"
    text = "New content"
    start_line = 1
    end_line = 2
    expected_error = f"File not found: {os.path.abspath(file_path)}"
    expected_error_code = "FILE_NOT_FOUND"

    with patch('os.path.isfile', return_value=False), \
         patch('os.path.abspath', return_value=os.path.abspath(file_path)), \
         patch('os.path.expanduser', return_value=file_path):
        
        result = edit_file(file_path, text, start_line, end_line)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "FILE_NOT_FOUND"

@pytest.mark.asyncio
async def test_edit_file_invalid_line_range():
    file_path = "/path/to/file.txt"
    text = "New content"
    start_line = 5
    end_line = 3
    expected_error = "Invalid line range specified."
    expected_error_code = "INVALID_LINE_RANGE"

    with patch('os.path.isfile', return_value=True), \
         patch('os.path.abspath', return_value=os.path.abspath(file_path)), \
         patch('os.path.expanduser', return_value=file_path):
        
        result = edit_file(file_path, text, start_line, end_line)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "INVALID_LINE_RANGE"

@pytest.mark.asyncio
async def test_edit_file_permission_denied():
    file_path = "/protected/path/file.txt"
    text = "New content"
    start_line = 1
    end_line = 2
    expected_error = f"Permission denied: [Errno 13] Permission denied: '{file_path}'"
    expected_error_code = "PERMISSION_DENIED"

    with patch('os.path.isfile', return_value=True), \
         patch('os.path.abspath', return_value=os.path.abspath(file_path)), \
         patch('os.path.expanduser', return_value=file_path), \
         patch('builtins.open', mock_open()) as mock_file:
        
        mock_file.side_effect = PermissionError("[Errno 13] Permission denied")
        result = edit_file(file_path, text, start_line, end_line)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "PERMISSION_DENIED"

@pytest.mark.asyncio
async def test_edit_file_os_error():
    file_path = "/path/to/file.txt"
    text = "New content"
    start_line = 1
    end_line = 2
    expected_error = f"OS error occurred: [Errno 22] Invalid argument: '{file_path}'"
    expected_error_code = "OS_ERROR"

    with patch('os.path.isfile', return_value=True), \
         patch('os.path.abspath', return_value=os.path.abspath(file_path)), \
         patch('os.path.expanduser', return_value=file_path), \
         patch('builtins.open', mock_open()) as mock_file:
        
        mock_file.side_effect = OSError("[Errno 22] Invalid argument")
        result = edit_file(file_path, text, start_line, end_line)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "OS_ERROR"

@pytest.mark.asyncio
async def test_edit_file_unexpected_error():
    file_path = "/path/to/file.txt"
    text = "New content"
    start_line = 1
    end_line = 2
    expected_error = f"Unexpected error: Unexpected exception"
    expected_error_code = "UNEXPECTED_ERROR"

    with patch('os.path.isfile', return_value=True), \
         patch('os.path.abspath', return_value=os.path.abspath(file_path)), \
         patch('os.path.expanduser', return_value=file_path), \
         patch('builtins.open', mock_open()) as mock_file:
        
        mock_file.side_effect = Exception("Unexpected exception")
        result = edit_file(file_path, text, start_line, end_line)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "UNEXPECTED_ERROR"