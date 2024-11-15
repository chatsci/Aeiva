# tools/move_mouse/test.py

import pytest
from unittest.mock import patch
from .api import move_mouse
import pyautogui

@pytest.mark.asyncio
async def test_move_mouse_success():
    x, y, duration = 500, 300, 1.0
    expected_output = f"Mouse moved to ({x}, {y}) over {duration} seconds."
    
    with patch('pyautogui.size', return_value=(1920, 1080)), \
         patch('pyautogui.moveTo') as mock_moveTo:
        
        result = move_mouse(x, y, duration)
        mock_moveTo.assert_called_with(x, y, duration=duration)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_move_mouse_negative_duration():
    x, y, duration = 500, 300, -1.0
    expected_error = "Duration cannot be negative."
    
    result = move_mouse(x, y, duration)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "INVALID_DURATION"

@pytest.mark.asyncio
async def test_move_mouse_coordinates_out_of_bounds():
    x, y, duration = 2000, 1200, 0.5
    expected_error = f"Coordinates ({x}, {y}) are out of screen bounds."
    
    with patch('pyautogui.size', return_value=(1920, 1080)):
        result = move_mouse(x, y, duration)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "COORDINATES_OUT_OF_BOUNDS"

@pytest.mark.asyncio
async def test_move_mouse_exception():
    x, y, duration = 500, 300, 0.5
    expected_error_code = "MOVE_MOUSE_FAILED"
    expected_error_message = "Error moving mouse: Sample exception."
    
    with patch('pyautogui.size', return_value=(1920, 1080)), \
         patch('pyautogui.moveTo', side_effect=Exception("Sample exception.")):
        
        result = move_mouse(x, y, duration)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "MOVE_MOUSE_FAILED"