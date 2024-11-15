# tools/open_application/test.py

import pytest
from unittest.mock import patch
from .api import open_application
import sys

@pytest.mark.asyncio
async def test_open_application_success_windows():
    application_path = "C:\\Program Files\\TestApp\\test.exe"
    expected_output = f"Application opened: {application_path}"
    
    with patch('os.path.exists', return_value=True), \
         patch('os.path.expanduser', return_value=application_path), \
         patch('os.startfile') as mock_startfile, \
         patch('sys.platform', 'win32'):
        
        result = open_application(application_path)
        mock_startfile.assert_called_once_with(application_path)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_open_application_success_macos():
    application_path = "/Applications/TestApp.app/Contents/MacOS/TestApp"
    expected_output = f"Application opened: {application_path}"
    
    with patch('os.path.exists', return_value=True), \
         patch('os.path.expanduser', return_value=application_path), \
         patch('subprocess.Popen') as mock_popen, \
         patch('sys.platform', 'darwin'):
        
        result = open_application(application_path)
        mock_popen.assert_called_once_with([application_path])
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_open_application_unsupported_os():
    application_path = "/path/to/app"
    expected_error = "Unsupported operating system."
    
    with patch('sys.platform', 'unknown_os'):
        result = open_application(application_path)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "UNSUPPORTED_OS"

@pytest.mark.asyncio
async def test_open_application_missing_application_path():
    application_path = ""
    expected_error = "Application path must be provided."
    
    result = open_application(application_path)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "MISSING_APPLICATION_PATH"

@pytest.mark.asyncio
async def test_open_application_application_not_found():
    application_path = "/non/existent/app.exe"
    expected_error = f"Application not found: {application_path}"
    
    with patch('os.path.exists', return_value=False), \
         patch('os.path.expanduser', return_value=application_path):
        
        result = open_application(application_path)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "APPLICATION_NOT_FOUND"

@pytest.mark.asyncio
async def test_open_application_exception():
    application_path = "/path/to/app"
    expected_error_code = "OPEN_APPLICATION_FAILED"
    expected_error_message = "Error opening application: Sample exception."
    
    with patch('os.path.exists', return_value=True), \
         patch('os.path.expanduser', return_value=application_path), \
         patch('subprocess.Popen', side_effect=Exception("Sample exception.")), \
         patch('sys.platform', 'linux'):
        
        result = open_application(application_path)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "OPEN_APPLICATION_FAILED"