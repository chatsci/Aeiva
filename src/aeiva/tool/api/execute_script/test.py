# tools/execute_script/test.py

import pytest
from unittest.mock import patch, MagicMock
from .api import execute_script

@pytest.mark.asyncio
async def test_execute_script_success_python():
    script_content = "print('Hello, World!')"
    language = "python"
    expected_output = "Script executed successfully:\nHello, World!\n"

    mock_completed_process = MagicMock()
    mock_completed_process.returncode = 0
    mock_completed_process.stdout = "Hello, World!\n"
    mock_completed_process.stderr = ""

    with patch('subprocess.run', return_value=mock_completed_process), \
         patch('tempfile.NamedTemporaryFile') as mock_tempfile, \
         patch('os.remove') as mock_remove:
        mock_tempfile.return_value.__enter__.return_value.name = "/tmp/temp_script.py"
        result = execute_script(script_content, language)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_execute_script_success_bash():
    script_content = "echo 'Hello, Bash!'"
    language = "bash"
    expected_output = "Script executed successfully:\nHello, Bash!\n"

    mock_completed_process = MagicMock()
    mock_completed_process.returncode = 0
    mock_completed_process.stdout = "Hello, Bash!\n"
    mock_completed_process.stderr = ""

    with patch('subprocess.run', return_value=mock_completed_process), \
         patch('tempfile.NamedTemporaryFile') as mock_tempfile, \
         patch('os.remove') as mock_remove, \
         patch('os.chmod'):
        mock_tempfile.return_value.__enter__.return_value.name = "/tmp/temp_script.sh"
        result = execute_script(script_content, language)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_execute_script_unsupported_language():
    script_content = "print('Hello')"
    language = "javascript"
    expected_error = "Unsupported script language. Choose 'python' or 'bash'."

    result = execute_script(script_content, language)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "UNSUPPORTED_LANGUAGE"

@pytest.mark.asyncio
async def test_execute_script_execution_failed():
    script_content = "print('Hello)"
    language = "python"
    expected_error_code = "SCRIPT_EXECUTION_FAILED"
    expected_error_message = "Script execution failed:\n  File \"/tmp/temp_script.py\", line 1\n    print('Hello)\n                ^\nSyntaxError: EOL while scanning string literal\n"

    mock_completed_process = MagicMock()
    mock_completed_process.returncode = 1
    mock_completed_process.stdout = ""
    mock_completed_process.stderr = "  File \"/tmp/temp_script.py\", line 1\n    print('Hello)\n                ^\nSyntaxError: EOL while scanning string literal\n"

    with patch('subprocess.run', return_value=mock_completed_process), \
         patch('tempfile.NamedTemporaryFile') as mock_tempfile, \
         patch('os.remove') as mock_remove:
        mock_tempfile.return_value.__enter__.return_value.name = "/tmp/temp_script.py"
        result = execute_script(script_content, language)
        assert result['output'] is None
        assert result['error'] == "Script execution failed:\n  File \"/tmp/temp_script.py\", line 1\n    print('Hello)\n                ^\nSyntaxError: EOL while scanning string literal\n"
        assert result['error_code'] == "SCRIPT_EXECUTION_FAILED"

@pytest.mark.asyncio
async def test_execute_script_timeout_expired():
    script_content = "import time\ntime.sleep(10)"
    language = "python"
    expected_error_code = "TIMEOUT_EXPIRED"
    expected_error_message = "Script execution timed out."

    with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='python /tmp/temp_script.py', timeout=5)), \
         patch('tempfile.NamedTemporaryFile') as mock_tempfile, \
         patch('os.remove') as mock_remove:
        mock_tempfile.return_value.__enter__.return_value.name = "/tmp/temp_script.py"
        result = execute_script(script_content, language)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "TIMEOUT_EXPIRED"

@pytest.mark.asyncio
async def test_execute_script_exception():
    script_content = "print('Hello')"
    language = "python"
    expected_error_code = "EXECUTION_FAILED"
    expected_error_message = "Error executing script: Sample exception."

    with patch('subprocess.run', side_effect=Exception("Sample exception.")):
        result = execute_script(script_content, language)
        assert result['output'] is None
        assert result['error'] == "Error executing script: Sample exception."
        assert result['error_code'] == "EXECUTION_FAILED"