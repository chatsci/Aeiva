# tools/close_application/test.py

import pytest
from unittest.mock import patch, MagicMock
from .api import close_application

@pytest.mark.asyncio
async def test_close_application_success():
    process_name = "test_process.exe"
    expected_output = f"Application '{process_name}' terminated."

    mock_proc = MagicMock()
    with patch('psutil.process_iter', return_value=[mock_proc]) as mock_process_iter:
        result = close_application(process_name)
        mock_proc.terminate.assert_called_once()
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_close_application_process_not_found():
    process_name = "non_existent_process.exe"

    with patch('psutil.process_iter', return_value=[]):
        result = close_application(process_name)
        assert result['output'] is None
        assert result['error'] == f"No running application found with name '{process_name}'."
        assert result['error_code'] == "PROCESS_NOT_FOUND"

@pytest.mark.asyncio
async def test_close_application_missing_process_name():
    process_name = ""

    result = close_application(process_name)
    assert result['output'] is None
    assert result['error'] == "Process name must be provided."
    assert result['error_code'] == "MISSING_PROCESS_NAME"

@pytest.mark.asyncio
async def test_close_application_exception():
    process_name = "error_process.exe"

    with patch('psutil.process_iter', side_effect=Exception("Sample exception.")):
        result = close_application(process_name)
        assert result['output'] is None
        assert result['error'] == "Error closing application: Sample exception."
        assert result['error_code'] == "CLOSE_APPLICATION_FAILED"