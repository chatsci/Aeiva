# tools/scroll/test.py

import pytest
from unittest.mock import patch
from .api import scroll

@pytest.mark.asyncio
async def test_scroll_success_up():
    direction = "up"
    lines = 50
    scroll_id = 1
    expected_output = f"Scrolled {direction} by {lines} lines. Scroll ID: {scroll_id}"
    
    with patch('pyautogui.scroll') as mock_scroll:
        result = scroll(direction=direction, lines=lines, scroll_id=scroll_id)
        mock_scroll.assert_called_once_with(lines)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_scroll_success_down():
    direction = "down"
    lines = 100
    scroll_id = 2
    expected_output = f"Scrolled {direction} by {lines} lines. Scroll ID: {scroll_id}"
    
    with patch('pyautogui.scroll') as mock_scroll:
        result = scroll(direction=direction, lines=lines, scroll_id=scroll_id)
        mock_scroll.assert_called_once_with(-lines)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_scroll_invalid_direction():
    direction = "left"
    lines = 100
    scroll_id = 3
    expected_error = "Invalid direction. Choose 'up' or 'down'."
    expected_error_code = "INVALID_DIRECTION"
    
    result = scroll(direction=direction, lines=lines, scroll_id=scroll_id)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == expected_error_code

@pytest.mark.asyncio
async def test_scroll_invalid_lines_low():
    direction = "up"
    lines = 0
    scroll_id = 4
    expected_error = "Lines must be between 1 and 1000."
    expected_error_code = "INVALID_LINES"
    
    result = scroll(direction=direction, lines=lines, scroll_id=scroll_id)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "INVALID_LINES"

@pytest.mark.asyncio
async def test_scroll_invalid_lines_high():
    direction = "down"
    lines = 1001
    scroll_id = 5
    expected_error = "Lines must be between 1 and 1000."
    expected_error_code = "INVALID_LINES"
    
    result = scroll(direction=direction, lines=lines, scroll_id=scroll_id)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "INVALID_LINES"

@pytest.mark.asyncio
async def test_scroll_exception():
    direction = "up"
    lines = 100
    scroll_id = 6
    expected_error_code = "SCROLL_FAILED"
    expected_error_message = "Error during scrolling: Sample exception."
    
    with patch('pyautogui.scroll', side_effect=Exception("Sample exception.")):
        result = scroll(direction=direction, lines=lines, scroll_id=scroll_id)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "SCROLL_FAILED"