# tools/type_keyboard/test.py

import pytest
from unittest.mock import patch
from .api import type_keyboard

@pytest.mark.asyncio
async def test_type_keyboard_success():
    text = "Hello, World!"
    interval = 0.1
    expected_output = f"Typed text: '{text}'"
    
    with patch('pyautogui.write') as mock_write:
        result = type_keyboard(text, interval)
        mock_write.assert_called_once_with(text, interval=interval)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_type_keyboard_missing_text():
    text = ""
    interval = 0.1
    expected_error = "Text to type must be provided."
    
    result = type_keyboard(text, interval)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "MISSING_TEXT"

@pytest.mark.asyncio
async def test_type_keyboard_invalid_interval():
    text = "Hello, World!"
    interval = -0.1
    expected_error = "Interval cannot be negative."
    
    result = type_keyboard(text, interval)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "INVALID_INTERVAL"

@pytest.mark.asyncio
async def test_type_keyboard_exception():
    text = "Hello, World!"
    interval = 0.1
    expected_error_code = "TYPE_KEYBOARD_FAILED"
    expected_error_message = "Error typing text: Sample exception."
    
    with patch('pyautogui.write', side_effect=Exception("Sample exception.")):
        result = type_keyboard(text, interval)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "TYPE_KEYBOARD_FAILED"