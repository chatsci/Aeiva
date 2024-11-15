# get_webpage_elements/test.py

import pytest
from unittest.mock import patch, MagicMock
from get_webpage_elements.api import get_webpage_elements
from model import GetWebpageElementsErrorCode
from selenium.common.exceptions import WebDriverException

@pytest.mark.parametrize("request, mock_elements, mock_attributes, mock_text, expected", [
    # Successful retrieval with elements
    (
        {
            "url": "http://example.com",
            "selector_type": "css",
            "selector": "div.container",
            "timeout": 5
        },
        [MagicMock(tag_name="div", text="Example Domain")],
        [{"name": "id", "value": "main"}, {"name": "class", "value": "container"}],
        "Example Domain",
        {
            "output": [
                {
                    "tag_name": "div",
                    "id": "main",
                    "class": "container",
                    "text": "Example Domain",
                    "attributes": {"id": "main", "class": "container"}
                }
            ],
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # No elements found
    (
        {
            "url": "http://example.com",
            "selector_type": "css",
            "selector": "span.nonexistent",
            "timeout": 5
        },
        [],
        [],
        "",
        {
            "output": [],
            "error": "No elements found matching the selector.",
            "error_code": "NO_ELEMENTS_FOUND"
        }
    ),
    # Unsupported selector type
    (
        {
            "url": "http://example.com",
            "selector_type": "unsupported",
            "selector": "div",
            "timeout": 5
        },
        None,
        None,
        None,
        {
            "output": None,
            "error": "Unsupported selector type: unsupported",
            "error_code": "INVALID_SELECTOR_TYPE"
        }
    ),
    # Validation error (missing required field)
    (
        {
            "url": "",
            "selector_type": "css",
            "selector": "div",
            "timeout": 5
        },
        None,
        None,
        None,
        {
            "output": None,
            "error": "Validation Error: 1 validation error for GetWebpageElementsParams\nurl\n  field required (type=value_error.missing)",
            "error_code": "VALIDATION_ERROR"
        }
    ),
    # WebDriver error
    (
        {
            "url": "http://example.com",
            "selector_type": "css",
            "selector": "div",
            "timeout": 5
        },
        None,
        None,
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
            "selector_type": "css",
            "selector": "div",
            "timeout": 5
        },
        None,
        None,
        None,
        {
            "output": None,
            "error": "Unexpected Error: Some unexpected error",
            "error_code": "UNEXPECTED_ERROR"
        }
    ),
])
def test_get_webpage_elements(request, mock_elements, mock_attributes, mock_text, expected):
    with patch('get_webpage_elements.api.webdriver.Chrome') as mock_webdriver:
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver

        # Mock driver.get
        mock_driver.get.return_value = None

        if mock_elements is not None:
            # Mock find_elements
            mock_driver.find_elements.return_value = mock_elements

            # Mock get_property for attributes
            for elem, attrs in zip(mock_elements, mock_attributes):
                elem.get_property.return_value = attrs

            # Mock get_attribute for id and class
            for elem in mock_elements:
                elem.get_attribute.side_effect = lambda attr: {
                    "id": "main",
                    "class": "container"
                }.get(attr, None)

            # Mock text
            for elem in mock_elements:
                elem.text = mock_text
        else:
            # Mock find_elements to return empty or raise exception based on error_code
            if expected["error_code"] == "INVALID_SELECTOR_TYPE":
                mock_driver.find_elements.return_value = []
            elif expected["error_code"] == "WEBDRIVER_ERROR":
                mock_driver.find_elements.side_effect = WebDriverException("invalid session id")
            else:
                mock_driver.find_elements.return_value = []

        # Mock driver.quit
        mock_driver.quit.return_value = None

        # Execute
        result = get_webpage_elements(request)

        # Assert
        assert result == expected