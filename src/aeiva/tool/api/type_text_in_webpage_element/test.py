# type_text_in_webpage_element/test.py

import pytest
from unittest.mock import patch, MagicMock
from type_text_in_webpage_element.api import type_text_in_webpage_element
from selenium.common.exceptions import WebDriverException, NoSuchElementException, ElementNotInteractableException

@pytest.mark.parametrize("request, mock_find_element_side_effect, mock_send_keys_side_effect, mock_clear_side_effect, expected", [
    # Successful typing without clearing existing text
    (
        {
            "selector": "#input",
            "selector_type": "css",
            "text": "Hello World",
            "clear_existing": False
        },
        None,  # No exception in find_element
        None,  # No exception in send_keys
        None,  # No exception in clear
        {
            "output": {
                "success": True,
                "element_found": True,
                "text_typed": "Hello World",
                "final_element_value": "Hello World",
                "is_visible": True,
                "is_enabled": True
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # Successful typing with clearing existing text
    (
        {
            "selector": "#input",
            "selector_type": "css",
            "text": "New Text",
            "clear_existing": True
        },
        None,
        None,
        None,
        {
            "output": {
                "success": True,
                "element_found": True,
                "text_typed": "New Text",
                "final_element_value": "New Text",
                "is_visible": True,
                "is_enabled": True
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # Missing required parameter 'text'
    (
        {
            "selector": "#input",
            "selector_type": "css",
            "clear_existing": True
        },
        None,
        None,
        None,
        {
            "output": None,
            "error": "Missing required parameter: text",
            "error_code": "VALIDATION_ERROR"
        }
    ),
    # Unsupported selector type
    (
        {
            "selector": "#input",
            "selector_type": "unsupported",
            "text": "Hello",
            "clear_existing": False
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
    # Element not found
    (
        {
            "selector": ".nonexistent",
            "selector_type": "css",
            "text": "Hello",
            "clear_existing": False
        },
        NoSuchElementException(),
        None,
        None,
        {
            "output": None,
            "error": "Element not found.",
            "error_code": "ELEMENT_NOT_FOUND"
        }
    ),
    # Element not visible or enabled
    (
        {
            "selector": "#hidden",
            "selector_type": "css",
            "text": "Hello",
            "clear_existing": False
        },
        None,
        None,
        None,
        {
            "output": {
                "success": False,
                "element_found": True,
                "is_visible": False,
                "is_enabled": True
            },
            "error": "Element is not visible or enabled.",
            "error_code": "ELEMENT_NOT_INTERACTABLE"
        }
    ),
    # WebDriver exception during find_element
    (
        {
            "selector": "#input",
            "selector_type": "css",
            "text": "Hello",
            "clear_existing": False
        },
        WebDriverException("Find element failed"),
        None,
        None,
        {
            "output": None,
            "error": "WebDriver Error during finding element: Find element failed",
            "error_code": "WEBDRIVER_ERROR"
        }
    ),
    # WebDriver exception during clear
    (
        {
            "selector": "#input",
            "selector_type": "css",
            "text": "Hello",
            "clear_existing": True
        },
        None,
        None,
        WebDriverException("Clear failed"),
        {
            "output": None,
            "error": "WebDriver Error during clearing text: Clear failed",
            "error_code": "WEBDRIVER_ERROR"
        }
    ),
    # WebDriver exception during send_keys
    (
        {
            "selector": "#input",
            "selector_type": "css",
            "text": "Hello",
            "clear_existing": False
        },
        None,
        WebDriverException("Send keys failed"),
        None,
        {
            "output": None,
            "error": "WebDriver Error during typing text: Send keys failed",
            "error_code": "WEBDRIVER_ERROR"
        }
    ),
    # Unexpected exception
    (
        {
            "selector": "#input",
            "selector_type": "css",
            "text": "Hello",
            "clear_existing": False
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
def test_type_text_in_webpage_element(request, mock_find_element_side_effect, mock_send_keys_side_effect, mock_clear_side_effect, expected):
    with patch('type_text_in_webpage_element.api.webdriver.Chrome') as mock_webdriver:
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver

        if mock_find_element_side_effect:
            mock_driver.find_element.side_effect = mock_find_element_side_effect
        else:
            mock_element = MagicMock()
            mock_driver.find_element.return_value = mock_element
            mock_element.is_displayed.return_value = True
            mock_element.is_enabled.return_value = True
            mock_element.get_attribute.return_value = request.get("text", "")
            if request.get("clear_existing", False):
                if mock_clear_side_effect:
                    mock_element.clear.side_effect = mock_clear_side_effect
                else:
                    mock_element.clear.return_value = None
            if mock_send_keys_side_effect:
                mock_element.send_keys.side_effect = mock_send_keys_side_effect
            else:
                mock_element.send_keys.return_value = None

            if "final_element_value" in expected["output"]:
                mock_element.get_attribute.return_value = expected["output"]["final_element_value"]

        # Execute
        result = type_text_in_webpage_element(request)

        # Assert
        assert result == expected