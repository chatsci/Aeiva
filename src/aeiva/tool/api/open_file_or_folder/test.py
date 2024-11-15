# tools/open_file_or_folder/test.py

import pytest
from unittest.mock import patch
from .api import open_file_or_folder
import sys

@pytest.mark.asyncio
async def test_open_file_or_folder_success_windows():
    path = "C:\\Users\\TestUser\\Documents\\test_document.txt"
    expected_output = f"Opened: {path}"
    
    with patch('os.path.exists', return_value=True), \
         patch('os.path.expanduser', return_value=path), \
         patch('os.startfile') as mock_startfile, \
         patch('sys.platform', 'win32'):
        
        result = open_file_or_folder(path)
        mock_startfile.assert_called_once_with(path)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_open_file_or_folder_success_macos():
    path = "/Users/testuser/Documents/test_document.txt"
    expected_output = f"Opened: {path}"
    
    with patch('os.path.exists', return_value=True), \
         patch('os.path.expanduser', return_value=path), \
         patch('subprocess.run') as mock_run, \
         patch('sys.platform', 'darwin'):
        
        mock_run.return_value = subprocess.CompletedProcess(args=['open', path], returncode=0)
        
        result = open_file_or_folder(path)
        mock_run.assert_called_once_with(['open', path], check=True)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_open_file_or_folder_success_linux():
    path = "/home/testuser/Documents/test_document.txt"
    expected_output = f"Opened: {path}"
    
    with patch('os.path.exists', return_value=True), \
         patch('os.path.expanduser', return_value=path), \
         patch('subprocess.run') as mock_run, \
         patch('sys.platform', 'linux'):
        
        mock_run.return_value = subprocess.CompletedProcess(args=['xdg-open', path], returncode=0)
        
        result = open_file_or_folder(path)
        mock_run.assert_called_once_with(['xdg-open', path], check=True)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_open_file_or_folder_unsupported_os():
    path = "/path/to/file.txt"
    expected_error = "Unsupported operating system."
    
    with patch('sys.platform', 'unknown_os'):
        result = open_file_or_folder(path)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "UNSUPPORTED_OS"

@pytest.mark.asyncio
async def test_open_file_or_folder_missing_path():
    path = ""
    expected_error = "Path must be provided."
    
    result = open_file_or_folder(path)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "MISSING_PATH"

@pytest.mark.asyncio
async def test_open_file_or_folder_path_not_found():
    path = "/non/existent/path.txt"
    expected_error = f"Path not found: {path}"
    
    with patch('os.path.exists', return_value=False), \
         patch('os.path.expanduser', return_value=path):
        
        result = open_file_or_folder(path)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "PATH_NOT_FOUND"

@pytest.mark.asyncio
async def test_open_file_or_folder_open_failed():
    path = "/path/to/file.txt"
    expected_error_code = "OPEN_FAILED"
    expected_error_message = f"Failed to open '{path}': Sample exception."
    
    with patch('os.path.exists', return_value=True), \
         patch('os.path.expanduser', return_value=path), \
         patch('subprocess.run', side_effect=Exception("Sample exception.")), \
         patch('sys.platform', 'linux'):
        
        result = open_file_or_folder(path)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "OPEN_FAILED"