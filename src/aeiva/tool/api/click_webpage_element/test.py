# click_webpage_element/test.py

import pytest
from unittest.mock import patch, MagicMock
from click_webpage_element.api import click_webpage_element
from model import ClickWebpageElementErrorCode
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchElementException,
    ElementNotInteractableException
)

@pytest.mark.parametrize("request, mock_elements, mock_error, expected", [
    # Successful click
    (
        {
            "url": "http://example.com",
            "selector_type": "css",
            "selector": "button.submit",
            "timeout": 5
        },
        [MagicMock(tag_name="button")],
        None,
        {
            "output": {
                "success": True,
                "element_found": True,
                "scrolled_into_view": True
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # Element not found
    (
        {
            "url": "http://example.com",
            "selector_type": "css",
            "selector": "button.nonexistent",
            "timeout": 5
        },
        None,
        None,
        {
            "output": None,
            "error": "Element not found.",
            "error_code": "ELEMENT_NOT_FOUND"
        }
    ),
    # Unsupported selector type
    (
        {
            "url": "http://example.com",
            "selector_type": "unsupported",
            "selector": "button.submit",
            "timeout": 5
        },
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
            "selector": "button.submit",
            "timeout": 5
        },
        None,
        None,
        {
            "output": None,
            "error": "Validation Error: 1 validation error for ClickWebpageElementParams\nurl\n  field required (type=value_error.missing)",
            "error_code": "VALIDATION_ERROR"
        }
    ),
    # Scroll failed
    (
        {
            "url": "http://example.com",
            "selector_type": "css",
            "selector": "button.submit",
            "timeout": 5
        },
        [MagicMock(tag_name="button")],
        "Scroll error",
        {
            "output": None,
            "error": "Error scrolling to element: Scroll error",
            "error_code": "SCROLL_FAILED"
        }
    ),
    # Element not interactable
    (
        {
            "url": "http://example.com",
            "selector_type": "css",
            "selector": "button.submit",
            "timeout": 5
        },
        [MagicMock(tag_name="button")],
        "Element not interactable",
        {
            "output": {
                "success": False,
                "element_found": True,
                "scrolled_into_view": True
            },
            "error": "Element not interactable: Element not interactable",
            "error_code": "ELEMENT_NOT_INTERACTABLE"
        }
    ),
    # WebDriver error
    (
        {
            "url": "http://example.com",
            "selector_type": "css",
            "selector": "button.submit",
            "timeout": 5
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
            "selector_type": "css",
            "selector": "button.submit",
            "timeout": 5
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
def test_click_webpage_element(request, mock_elements, mock_error, expected):
    with patch('click_webpage_element.api.webdriver.Chrome') as mock_webdriver:
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver

        if mock_elements is not None:
            # Mock find_element
            mock_driver.find_element.return_value = mock_elements[0]

            # Mock execute_script for scrolling
            if expected["error_code"] == "SCROLL_FAILED":
                mock_driver.execute_script.side_effect = WebDriverException(mock_error)
            else:
                mock_driver.execute_script.return_value = None

            # Mock click
            if expected["error_code"] == "ELEMENT_NOT_INTERACTABLE":
                mock_driver.find_element.return_value.click.side_effect = ElementNotInteractableException("Element not interactable")
            elif expected["error_code"] == "SUCCESS":
                mock_driver.find_element.return_value.click.return_value = None
        else:
            # Mock find_element to raise NoSuchElementException or WebDriverException
            if expected["error_code"] == "WEBDRIVER_ERROR":
                mock_driver.find_element.side_effect = WebDriverException(mock_error)
            else:
                mock_driver.find_element.side_effect = NoSuchElementException()

        # Mock driver.quit
        mock_driver.quit.return_value = None

        # Execute
        result = click_webpage_element(request)

        # Assert
        assert result == expected