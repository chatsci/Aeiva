# navigate_browser_history/test.py

import pytest
from unittest.mock import patch, MagicMock
from navigate_browser_history.api import navigate_browser_history
from selenium.common.exceptions import WebDriverException

@pytest.mark.parametrize("request, mock_get_side_effect, expected", [
    # Successful navigation back
    (
        {
            "direction": "back",
            "steps": 2
        },
        None,  # No exception
        {
            "output": {
                "success": True,
                "previous_url": "http://example.com/page2",
                "message": "Navigated back by 2 step(s)."
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # Successful navigation forward
    (
        {
            "direction": "forward",
            "steps": 1
        },
        None,
        {
            "output": {
                "success": True,
                "previous_url": "http://example.com/page2",
                "message": "Navigated forward by 1 step(s)."
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    ),
    # Invalid direction
    (
        {
            "direction": "left",
            "steps": 1
        },
        None,
        {
            "output": None,
            "error": "Invalid direction: left. Must be 'back' or 'forward'.",
            "error_code": "INVALID_DIRECTION"
        }
    ),
    # Invalid steps (zero)
    (
        {
            "direction": "back",
            "steps": 0
        },
        None,
        {
            "output": None,
            "error": "Invalid steps: 0. Must be an integer >= 1.",
            "error_code": "INVALID_STEPS"
        }
    ),
    # Invalid steps (non-integer)
    (
        {
            "direction": "forward",
            "steps": "two"
        },
        None,
        {
            "output": None,
            "error": "Invalid steps: two. Must be an integer >= 1.",
            "error_code": "INVALID_STEPS"
        }
    ),
    # WebDriver exception during navigation
    (
        {
            "direction": "back",
            "steps": 1
        },
        WebDriverException("Session not created"),
        {
            "output": None,
            "error": "WebDriver Error during navigation: Session not created",
            "error_code": "WEBDRIVER_ERROR"
        }
    ),
    # Unexpected exception
    (
        {
            "direction": "forward",
            "steps": 1
        },
        Exception("Some unexpected error"),
        {
            "output": None,
            "error": "Unexpected Error: Some unexpected error",
            "error_code": "UNEXPECTED_ERROR"
        }
    ),
])
def test_navigate_browser_history(request, mock_get_side_effect, expected):
    with patch('navigate_browser_history.api.webdriver.Chrome') as mock_webdriver:
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver

        if mock_get_side_effect:
            mock_driver.get.side_effect = mock_get_side_effect
        else:
            mock_driver.get.return_value = None

        # Mock driver.current_url
        mock_driver.current_url = "http://example.com/page2"

        # Mock driver.back and driver.forward
        if not mock_get_side_effect:
            mock_driver.back.return_value = None
            mock_driver.forward.return_value = None

        # Mock driver.quit
        mock_driver.quit.return_value = None

        # Execute
        result = navigate_browser_history(request)

        # Assert
        assert result == expected