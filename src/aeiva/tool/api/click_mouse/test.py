# tools/click_mouse/test.py

import pytest
from unittest.mock import patch
from .api import click_mouse

@pytest.mark.asyncio
async def test_click_mouse_success():
    button = "left"
    clicks = 2
    interval = 0.1
    expected_output = "Mouse clicked 2 time(s) with left button."

    with patch('pyautogui.click') as mock_click:
        result = click_mouse(button=button, clicks=clicks, interval=interval)
        mock_click.assert_called_with(button=button, clicks=clicks, interval=interval)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_click_mouse_invalid_button():
    button = "invalid_button"
    clicks = 1
    interval = 0.0
    expected_error = "Invalid button type: invalid_button. Choose from 'left', 'right', or 'middle'."

    result = click_mouse(button=button, clicks=clicks, interval=interval)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "INVALID_BUTTON_TYPE"

@pytest.mark.asyncio
async def test_click_mouse_invalid_clicks():
    button = "left"
    clicks = 0
    interval = 0.0
    expected_error = "Number of clicks must be at least 1."

    result = click_mouse(button=button, clicks=clicks, interval=interval)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "INVALID_CLICKS"

@pytest.mark.asyncio
async def test_click_mouse_invalid_interval():
    button = "left"
    clicks = 1
    interval = -0.5
    expected_error = "Interval between clicks cannot be negative."

    result = click_mouse(button=button, clicks=clicks, interval=interval)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "INVALID_INTERVAL"

@pytest.mark.asyncio
async def test_click_mouse_exception():
    button = "left"
    clicks = 1
    interval = 0.0
    expected_error_code = "CLICK_FAILED"
    expected_error_message = "Error clicking mouse: Sample exception."

    with patch('pyautogui.click', side_effect=Exception("Sample exception.")):
        result = click_mouse(button=button, clicks=clicks, interval=interval)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == expected_error_code