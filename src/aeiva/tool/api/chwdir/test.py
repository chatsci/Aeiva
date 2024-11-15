# test.py

import pytest
from unittest.mock import patch
from .api import chwdir
import os

@pytest.mark.asyncio
async def test_chwdir_success():
    path = "/new/path"
    expected_output = f"Changed working directory to {os.path.abspath(path)}"

    with patch('os.chdir') as mock_chdir, \
         patch('os.path.abspath', return_value=os.path.abspath(path)), \
         patch('os.path.expanduser', return_value=path):
        
        result = chwdir(path)
        mock_chdir.assert_called_once_with(os.path.abspath(path))
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_chwdir_empty_path():
    path = "   "
    expected_error = "Path cannot be empty or just whitespace."
    expected_error_code = "EMPTY_PATH"

    result = chwdir(path)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == expected_error_code

@pytest.mark.asyncio
async def test_chwdir_permission_denied():
    path = "/protected/path"
    expected_error_code = "PERMISSION_DENIED"
    expected_error_message = f"Permission denied: [Errno 13] Permission denied: '{path}'"

    with patch('os.path.abspath', return_value=os.path.abspath(path)), \
         patch('os.path.expanduser', return_value=path), \
         patch('os.chdir', side_effect=PermissionError("Permission denied")):
        
        result = chwdir(path)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == expected_error_code

@pytest.mark.asyncio
async def test_chwdir_directory_not_found():
    path = "/nonexistent/path"
    expected_error_code = "DIRECTORY_NOT_FOUND"
    expected_error_message = f"Directory not found: [Errno 2] No such file or directory: '{path}'"

    with patch('os.path.abspath', return_value=os.path.abspath(path)), \
         patch('os.path.expanduser', return_value=path), \
         patch('os.chdir', side_effect=FileNotFoundError(f"No such file or directory: '{path}'")):
        
        result = chwdir(path)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "DIRECTORY_NOT_FOUND"

@pytest.mark.asyncio
async def test_chwdir_runtime_error():
    path = "/some/path"
    expected_error_code = "RUNTIME_ERROR"
    expected_error_message = f"Unable to resolve path: Runtime error"

    with patch('os.path.abspath', return_value=os.path.abspath(path)), \
         patch('os.path.expanduser', return_value=path), \
         patch('os.chdir', side_effect=RuntimeError("Runtime error")):
        
        result = chwdir(path)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "RUNTIME_ERROR"

@pytest.mark.asyncio
async def test_chwdir_os_error():
    path = "/another/path"
    expected_error_code = "OS_ERROR"
    expected_error_message = f"OS error occurred: OSError occurred"

    with patch('os.path.abspath', return_value=os.path.abspath(path)), \
         patch('os.path.expanduser', return_value=path), \
         patch('os.chdir', side_effect=OSError("OSError occurred")):
        
        result = chwdir(path)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "OS_ERROR"

@pytest.mark.asyncio
async def test_chwdir_unexpected_error():
    path = "/unexpected/path"
    expected_error_code = "UNEXPECTED_ERROR"
    expected_error_message = f"Unexpected error: Unexpected exception"

    with patch('os.path.abspath', return_value=os.path.abspath(path)), \
         patch('os.path.expanduser', return_value=path), \
         patch('os.chdir', side_effect=Exception("Unexpected exception")):
        
        result = chwdir(path)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "UNEXPECTED_ERROR"