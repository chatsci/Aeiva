# tools/read_file/test.py

import pytest
from unittest.mock import patch, mock_open
from .api import read_file

@pytest.mark.asyncio
async def test_read_file_success():
    file_path = "/path/to/file.txt"
    file_content = "Hello, World!"
    
    with patch('os.path.isfile', return_value=True), \
         patch('os.path.expanduser', return_value=file_path), \
         patch('builtins.open', mock_open(read_data=file_content)):
        
        result = read_file(file_path)
        assert result['output'] == file_content
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_read_file_missing_file_path():
    file_path = ""
    expected_error = "File path must be provided."
    
    result = read_file(file_path)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "MISSING_FILE_PATH"

@pytest.mark.asyncio
async def test_read_file_file_not_found():
    file_path = "/path/to/nonexistent_file.txt"
    expected_error = f"File not found: {file_path}"
    
    with patch('os.path.isfile', return_value=False), \
         patch('os.path.expanduser', return_value=file_path):
        
        result = read_file(file_path)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "FILE_NOT_FOUND"

@pytest.mark.asyncio
async def test_read_file_exception():
    file_path = "/path/to/file.txt"
    expected_error_code = "READ_FILE_FAILED"
    expected_error_message = "Error reading file: Sample exception."
    
    with patch('os.path.isfile', return_value=True), \
         patch('os.path.expanduser', return_value=file_path), \
         patch('builtins.open', side_effect=Exception("Sample exception.")):
        
        result = read_file(file_path)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == expected_error_code