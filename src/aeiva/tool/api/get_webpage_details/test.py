# get_webpage_details/test.py

import pytest
from unittest.mock import patch, MagicMock
from get_webpage_details.api import get_webpage_details
from model import GetWebpageDetailsErrorCode
from selenium.common.exceptions import WebDriverException

@pytest.mark.parametrize("request, mock_page_details, expected", [
    # Successful retrieval with accessibility snapshot
    (
        {
            "url": "http://example.com",
            "include_accessibility": True
        },
        {
            "title": "Example Domain",
            "url": "http://example.com",
            "metaTags": [],
            "accessibilitySnapshot": None
        },
        {
            "output": {
                "title": "Example Domain",
                "url": "http://example.com",
                "metaTags": [],
                "accessibilitySnapshot": None
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # Successful retrieval without accessibility snapshot
    (
        {
            "url": "http://example.com",
            "include_accessibility": False
        },
        {
            "title": "Example Domain",
            "url": "http://example.com",
            "metaTags": []
            # accessibilitySnapshot should be removed
        },
        {
            "output": {
                "title": "Example Domain",
                "url": "http://example.com",
                "metaTags": []
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # Validation error (missing required field)
    (
        {
            "url": "",
            "include_accessibility": True
        },
        None,
        {
            "output": None,
            "error": "Validation Error: 1 validation error for GetWebpageDetailsParams\nurl\n  field required (type=value_error.missing)",
            "error_code": "VALIDATION_ERROR"
        }
    ),
    # WebDriver error
    (
        {
            "url": "http://example.com",
            "include_accessibility": True
        },
        None,
        {
            "output": None,
            "error": "WebDriver Error: Message: invalid session id",
            "error_code": "WEBDRIVER_ERROR"
        }
    ),
    # Unexpected error
    (
        {
            "url": "http://example.com",
            "include_accessibility": True
        },
        None,
        {
            "output": None,
            "error": "Unexpected Error: Some unexpected error",
            "error_code": "UNEXPECTED_ERROR"
        }
    ),
])
def test_get_webpage_details(request, mock_page_details, expected):
    with patch('get_webpage_details.api.webdriver.Chrome') as mock_webdriver:
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver

        if mock_page_details is not None:
            # Mock driver.get
            mock_driver.get.return_value = None

            # Mock execute_script
            mock_driver.execute_script.return_value = mock_page_details
        else:
            # Mock driver.get to raise WebDriverException or other exceptions
            if expected["error_code"] == "WEBDRIVER_ERROR":
                mock_driver.get.side_effect = WebDriverException("invalid session id")
            else:
                mock_driver.get.return_value = None
                mock_driver.execute_script.side_effect = Exception("Some unexpected error")

        # Mock driver.quit
        mock_driver.quit.return_value = None

        # Execute
        result = get_webpage_details(request)

        # Assert
        assert result == expected