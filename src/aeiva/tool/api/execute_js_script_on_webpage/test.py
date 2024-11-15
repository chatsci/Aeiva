# execute_js_script_on_webpage/test.py

import pytest
from unittest.mock import patch, MagicMock
from execute_js_script_on_webpage.api import execute_js_script_on_webpage
from model import ExecuteJSScriptErrorCode
from selenium.common.exceptions import WebDriverException

@pytest.mark.parametrize("request, mock_result, mock_error, expected", [
    # Successful script execution without arguments
    (
        {
            "url": "http://example.com",
            "script": "return document.title;",
            "args": []
        },
        "Example Domain",
        None,
        {
            "output": {
                "result": "Example Domain"
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # Successful script execution with arguments
    (
        {
            "url": "http://example.com",
            "script": "return arguments[0] + arguments[1];",
            "args": [5, 10]
        },
        15,
        None,
        {
            "output": {
                "result": 15
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # Validation error (missing required field)
    (
        {
            "script": "return document.title;",
            "args": []
        },
        None,
        None,
        {
            "output": None,
            "error": "Validation Error: 1 validation error for ExecuteJSScriptParams\nurl\n  field required (type=value_error.missing)",
            "error_code": "VALIDATION_ERROR"
        }
    ),
    # Validation error (missing script)
    (
        {
            "url": "http://example.com",
            "args": []
        },
        None,
        None,
        {
            "output": None,
            "error": "Validation Error: 1 validation error for ExecuteJSScriptParams\nscript\n  field required (type=value_error.missing)",
            "error_code": "VALIDATION_ERROR"
        }
    ),
    # JavaScript execution error
    (
        {
            "url": "http://example.com",
            "script": "return nonExistentFunction();",
            "args": []
        },
        None,
        "JavaScript execution failed",
        {
            "output": None,
            "error": "JavaScript Execution Error: JavaScript execution failed",
            "error_code": "JS_EXECUTION_ERROR"
        }
    ),
    # WebDriver error
    (
        {
            "url": "http://example.com",
            "script": "return document.title;",
            "args": []
        },
        None,
        "WebDriver session error",
        {
            "output": None,
            "error": "WebDriver Error: WebDriver session error",
            "error_code": "WEBDRIVER_ERROR"
        }
    ),
    # Unexpected error
    (
        {
            "url": "http://example.com",
            "script": "return document.title;",
            "args": []
        },
        None,
        "Some unexpected error",
        {
            "output": None,
            "error": "Unexpected Error: Some unexpected error",
            "error_code": "UNEXPECTED_ERROR"
        }
    ),
])
def test_execute_js_script_on_webpage(request, mock_result, mock_error, expected):
    with patch('execute_js_script_on_webpage.api.webdriver.Chrome') as mock_webdriver:
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver

        if mock_error == "WebDriver session error":
            # Simulate WebDriverException during driver.get
            mock_driver.get.side_effect = WebDriverException(mock_error)
        elif mock_error == "JavaScript execution failed":
            # Simulate WebDriverException during execute_script
            mock_driver.execute_script.side_effect = WebDriverException(mock_error)
        elif mock_result is not None:
            # Mock driver.execute_script to return a result
            mock_driver.execute_script.return_value = mock_result
        else:
            # Simulate unexpected exception
            mock_driver.execute_script.side_effect = Exception(mock_error)

        # Mock driver.get
        if mock_error != "WebDriver session error" and mock_error != "JavaScript execution failed":
            mock_driver.get.return_value = None

        # Mock driver.quit
        mock_driver.quit.return_value = None

        # Execute
        result = execute_js_script_on_webpage(request)

        # Assert
        assert result == expected