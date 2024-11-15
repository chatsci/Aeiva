# scroll_webpage/test.py

import pytest
from unittest.mock import patch, MagicMock
from scroll_webpage.api import scroll_webpage
from selenium.common.exceptions import WebDriverException, NoSuchElementException

@pytest.mark.parametrize("request, mock_find_element_side_effect, mock_execute_scroll_side_effect, expected", [
    # Successful pixel-based scroll down
    (
        {
            "scroll_type": "pixels",
            "direction": "down",
            "amount": 300
        },
        None,  # No exception in find_element
        None,  # No exception in execute_script
        {
            "output": {
                "success": True,
                "scrolled_amount": 300
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # Successful pixel-based scroll up with default amount
    (
        {
            "scroll_type": "pixels",
            "direction": "up"
            # amount defaults to 200
        },
        None,
        None,
        {
            "output": {
                "success": True,
                "scrolled_amount": 200
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # Successful element-based scroll
    (
        {
            "scroll_type": "element",
            "direction": "down",
            "selector": "#footer",
            "selector_type": "css"
        },
        None,  # No exception in find_element
        None,  # No exception in execute_script
        {
            "output": {
                "success": True,
                "element_found": True
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # Scroll_type invalid
    (
        {
            "scroll_type": "diagonal",
            "direction": "down",
            "amount": 200
        },
        None,
        None,
        {
            "output": None,
            "error": "Invalid scroll_type: diagonal. Must be 'pixels' or 'element'.",
            "error_code": "INVALID_SCROLL_TYPE"
        }
    ),
    # Direction invalid
    (
        {
            "scroll_type": "pixels",
            "direction": "forward",
            "amount": 200
        },
        None,
        None,
        {
            "output": None,
            "error": "Invalid direction: forward. Must be 'up', 'down', 'left', or 'right'.",
            "error_code": "INVALID_DIRECTION"
        }
    ),
    # Missing selector for element scroll_type
    (
        {
            "scroll_type": "element",
            "direction": "down"
            # Missing selector
        },
        None,
        None,
        {
            "output": None,
            "error": "Selector must be provided for 'element' scroll_type.",
            "error_code": "MISSING_SELECTOR"
        }
    ),
    # Element not found for element scroll_type
    (
        {
            "scroll_type": "element",
            "direction": "down",
            "selector": ".nonexistent",
            "selector_type": "css"
        },
        NoSuchElementException(),
        None,
        {
            "output": None,
            "error": "Element not found with selector: .nonexistent",
            "error_code": "ELEMENT_NOT_FOUND"
        }
    ),
    # WebDriver exception during pixel scroll
    (
        {
            "scroll_type": "pixels",
            "direction": "down",
            "amount": 200
        },
        None,
        WebDriverException("Scrolling failed"),
        {
            "output": None,
            "error": "WebDriver Error during scrolling: Scrolling failed",
            "error_code": "WEBDRIVER_ERROR"
        }
    ),
    # WebDriver exception during element scroll
    (
        {
            "scroll_type": "element",
            "direction": "down",
            "selector": "#header",
            "selector_type": "css"
        },
        None,
        WebDriverException("Scrolling to element failed"),
        {
            "output": None,
            "error": "WebDriver Error during scrolling to element: Scrolling to element failed",
            "error_code": "WEBDRIVER_ERROR"
        }
    ),
    # Unexpected exception
    (
        {
            "scroll_type": "pixels",
            "direction": "down",
            "amount": 200
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
def test_scroll_webpage(request, mock_find_element_side_effect, mock_execute_scroll_side_effect, expected):
    with patch('scroll_webpage.api.webdriver.Chrome') as mock_webdriver:
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver

        # Handle element-based scroll
        if request.get("scroll_type", "pixels") == "element":
            if isinstance(mock_find_element_side_effect, Exception):
                mock_driver.find_element.side_effect = mock_find_element_side_effect
            else:
                mock_driver.find_element.return_value = MagicMock()
                if mock_execute_scroll_side_effect:
                    mock_driver.execute_script.side_effect = mock_execute_scroll_side_effect
                else:
                    mock_driver.execute_script.return_value = None
        elif request.get("scroll_type", "pixels") == "pixels":
            if isinstance(mock_execute_scroll_side_effect, Exception):
                mock_driver.execute_script.side_effect = mock_execute_scroll_side_effect
            else:
                mock_driver.execute_script.return_value = None

        # Mock driver.quit
        if not isinstance(mock_execute_scroll_side_effect, str):
            mock_driver.quit.return_value = None

        # Execute
        result = scroll_webpage(request)

        # Assert
        assert result == expected