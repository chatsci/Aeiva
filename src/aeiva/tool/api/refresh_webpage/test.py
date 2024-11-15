# refresh_webpage/test.py

import pytest
from unittest.mock import patch, MagicMock
from refresh_webpage.api import refresh_webpage
from selenium.common.exceptions import WebDriverException

@pytest.mark.parametrize("request, mock_refresh_side_effect, expected", [
    # Successful refresh without ignoring cache
    (
        {
            "ignore_cache": False
        },
        None,  # No exception
        {
            "output": {
                "success": True,
                "previous_url": "http://example.com",
                "new_url": None
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # Successful refresh with ignoring cache
    (
        {
            "ignore_cache": True
        },
        None,
        {
            "output": {
                "success": True,
                "previous_url": "http://example.com",
                "new_url": None
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # Missing optional parameter (use defaults)
    (
        {},
        None,
        {
            "output": {
                "success": True,
                "previous_url": "http://example.com",
                "new_url": None
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # WebDriver exception during refresh
    (
        {
            "ignore_cache": False
        },
        WebDriverException("Refresh failed"),
        {
            "output": None,
            "error": "WebDriver Error during refresh: Refresh failed",
            "error_code": "WEBDRIVER_ERROR"
        }
    ),
    # Unexpected exception
    (
        {
            "ignore_cache": False
        },
        "Some unexpected error",
        {
            "output": None,
            "error": "Unexpected Error: Some unexpected error",
            "error_code": "UNEXPECTED_ERROR"
        }
    ),
])
def test_refresh_webpage(request, mock_refresh_side_effect, expected):
    with patch('refresh_webpage.api.webdriver.Chrome') as mock_webdriver:
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver

        if mock_refresh_side_effect == "Some unexpected error":
            mock_driver.refresh.side_effect = Exception(mock_refresh_side_effect)
        elif isinstance(mock_refresh_side_effect, WebDriverException):
            mock_driver.refresh.side_effect = mock_refresh_side_effect
        else:
            mock_driver.refresh.return_value = None
            mock_driver.execute_script.return_value = None

        # Mock driver.current_url
        mock_driver.current_url = "http://example.com"

        # Mock driver.quit
        mock_driver.quit.return_value = None

        # Execute
        result = refresh_webpage(request)

        # Assert
        assert result == expected