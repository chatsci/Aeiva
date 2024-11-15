# navigate_to_webpage/test.py

import pytest
from unittest.mock import patch, MagicMock
from navigate_to_webpage.api import navigate_to_webpage
from selenium.common.exceptions import WebDriverException

@pytest.mark.parametrize("request, mock_get_side_effect, expected", [
    # Successful navigation
    (
        {
            "url": "http://example.com",
            "timeout": 5000
        },
        None,  # No exception
        {
            "output": {"message": "Navigated to the specified webpage."},
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # Missing required parameter
    (
        {
            "timeout": 5000
        },
        None,
        {
            "output": None,
            "error": "Missing required parameter: url",
            "error_code": "VALIDATION_ERROR"
        }
    ),
    # WebDriver exception during navigation
    (
        {
            "url": "http://example.com",
            "timeout": 5000
        },
        WebDriverException("Session not created"),
        {
            "output": None,
            "error": "WebDriver Error: Session not created",
            "error_code": "WEBDRIVER_ERROR"
        }
    ),
    # Unexpected exception
    (
        {
            "url": "http://example.com",
            "timeout": 5000
        },
        Exception("Unexpected error"),
        {
            "output": None,
            "error": "Unexpected Error: Unexpected error",
            "error_code": "UNEXPECTED_ERROR"
        }
    ),
])
def test_navigate_to_webpage(request, mock_get_side_effect, expected):
    with patch('navigate_to_webpage.api.webdriver.Chrome') as mock_webdriver:
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver

        if mock_get_side_effect:
            mock_driver.get.side_effect = mock_get_side_effect
        else:
            mock_driver.get.return_value = None

        # Mock driver.quit
        mock_driver.quit.return_value = None

        result = navigate_to_webpage(request)

        assert result == expected