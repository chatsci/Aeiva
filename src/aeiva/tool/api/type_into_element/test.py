# tools/type_into_element/test.py

import pytest
from unittest.mock import patch
from .api import type_into_element

@pytest.mark.asyncio
async def test_type_into_element_success():
    position = {'x': 100, 'y': 200, 'width': 50, 'height': 20}
    text = "Hello, World!"
    expected_output = "Typed into element at (125.0, 210.0)."
    
    with patch('pyautogui.size', return_value=(1920, 1080)), \
         patch('pyautogui.click') as mock_click, \
         patch('pyautogui.write') as mock_write:
        
        result = type_into_element(position, text)
        mock_click.assert_called_once_with(125.0, 210.0)
        mock_write.assert_called_once_with(text, interval=0.05)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_type_into_element_missing_position_key():
    position = {'x': 100, 'y': 200, 'width': 50}  # Missing 'height'
    text = "Hello, World!"
    expected_error = "Missing key 'height' in position dictionary."
    
    result = type_into_element(position, text)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "MISSING_POSITION_KEY"

@pytest.mark.asyncio
async def test_type_into_element_position_out_of_bounds():
    position = {'x': 2000, 'y': 1200, 'width': 50, 'height': 20}
    text = "Hello, World!"
    expected_error = "Coordinates (2025.0, 1210.0) are out of screen bounds."
    
    with patch('pyautogui.size', return_value=(1920, 1080)):
        result = type_into_element(position, text)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "POSITION_OUT_OF_BOUNDS"

@pytest.mark.asyncio
async def test_type_into_element_exception():
    position = {'x': 100, 'y': 200, 'width': 50, 'height': 20}
    text = "Hello, World!"
    expected_error_code = "TYPE_INTO_ELEMENT_FAILED"
    expected_error_message = "Error typing into element: Sample exception."
    
    with patch('pyautogui.size', return_value=(1920, 1080)), \
         patch('pyautogui.click', side_effect=Exception("Sample exception.")), \
         patch('pyautogui.write'):
        
        result = type_into_element(position, text)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "TYPE_INTO_ELEMENT_FAILED"