# tools/click_on_element/test.py

import pytest
from unittest.mock import patch
from .api import click_on_element
import pyautogui

@pytest.mark.asyncio
async def test_click_on_element_success():
    position = {"x": 100, "y": 200, "width": 50, "height": 20}
    expected_output = "Clicked on element at (125.0, 210.0)."

    with patch('pyautogui.click') as mock_click, \
         patch('pyautogui.size', return_value=pyautogui.Size(width=1920, height=1080)):
        result = click_on_element(position)
        mock_click.assert_called_with(125.0, 210.0)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_click_on_element_missing_key():
    position = {"x": 100, "y": 200, "width": 50}  # Missing 'height'
    expected_error = "Missing key 'height' in position dictionary."

    result = click_on_element(position)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "MISSING_POSITION_KEY"

@pytest.mark.asyncio
async def test_click_on_element_position_out_of_bounds():
    position = {"x": 1900, "y": 1000, "width": 50, "height": 50}
    expected_error = "Position (1925.0, 1025.0) is out of screen bounds."

    with patch('pyautogui.size', return_value=pyautogui.Size(width=1920, height=1080)):
        result = click_on_element(position)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "POSITION_OUT_OF_BOUNDS"

@pytest.mark.asyncio
async def test_click_on_element_exception():
    position = {"x": 100, "y": 200, "width": 50, "height": 20}
    expected_error_code = "CLICK_ELEMENT_FAILED"
    expected_error_message = "Error clicking on element: Sample exception."

    with patch('pyautogui.click', side_effect=Exception("Sample exception.")), \
         patch('pyautogui.size', return_value=pyautogui.Size(width=1920, height=1080)):
        result = click_on_element(position)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == expected_error_code