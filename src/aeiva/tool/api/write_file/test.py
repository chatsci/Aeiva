# tools/write_file/test.py

import pytest
from unittest.mock import patch, mock_open
from .api import write_file

@pytest.mark.asyncio
async def test_write_file_success_existing_directory():
    file_path = "/path/to/file.txt"
    content = "Hello, World!"
    expected_output = f"Content written to {file_path}"
    
    with patch('os.path.exists', return_value=True), \
         patch('os.path.expanduser', return_value=file_path), \
         patch('builtins.open', mock_open()) as mock_file:
        
        result = write_file(file_path, content)
        mock_file.assert_called_once_with(file_path, 'w', encoding='utf-8')
        mock_file().write.assert_called_once_with(content)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_write_file_success_create_directory():
    file_path = "/new/path/to/file.txt"
    content = "Hello, World!"
    directory = "/new/path/to"
    expected_output = f"Content written to {file_path}"
    
    with patch('os.path.exists', side_effect=lambda x: False if x == directory else True), \
         patch('os.makedirs') as mock_makedirs, \
         patch('os.path.expanduser', return_value=file_path), \
         patch('builtins.open', mock_open()) as mock_file:
        
        result = write_file(file_path, content)
        mock_makedirs.assert_called_once_with(directory, exist_ok=True)
        mock_file.assert_called_once_with(file_path, 'w', encoding='utf-8')
        mock_file().write.assert_called_once_with(content)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_write_file_missing_file_path():
    file_path = ""
    content = "Hello, World!"
    expected_error = "File path must be provided."
    
    result = write_file(file_path, content)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "MISSING_FILE_PATH"

@pytest.mark.asyncio
async def test_write_file_create_directory_failed():
    file_path = "/new/path/to/file.txt"
    content = "Hello, World!"
    directory = "/new/path/to"
    expected_error_code = "CREATE_DIRECTORY_FAILED"
    expected_error_message = "Error creating directory: Sample exception."
    
    with patch('os.path.exists', side_effect=lambda x: False if x == directory else True), \
         patch('os.makedirs', side_effect=Exception("Sample exception.")), \
         patch('os.path.expanduser', return_value=file_path):
        
        result = write_file(file_path, content)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "CREATE_DIRECTORY_FAILED"

@pytest.mark.asyncio
async def test_write_file_write_failed():
    file_path = "/path/to/file.txt"
    content = "Hello, World!"
    expected_error_code = "WRITE_FILE_FAILED"
    expected_error_message = "Error writing to file: Sample exception."
    
    with patch('os.path.exists', return_value=True), \
         patch('os.path.expanduser', return_value=file_path), \
         patch('builtins.open', mock_open()) as mock_file:
        
        mock_file.side_effect = Exception("Sample exception.")
        result = write_file(file_path, content)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "WRITE_FILE_FAILED"