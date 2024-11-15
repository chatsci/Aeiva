# tools/take_screenshot/test.py

import pytest
from unittest.mock import patch, MagicMock
from .api import take_screenshot

@pytest.mark.asyncio
async def test_take_screenshot_success_default_save_path():
    save_path = "/screenshots/screenshot_20230101_123456.png"
    expected_output = f"Screenshot saved to {save_path}"
    
    with patch('dotenv.load_dotenv'), \
         patch('os.getenv', return_value="/screenshots"), \
         patch('pyautogui.screenshot') as mock_screenshot, \
         patch('datetime.datetime') as mock_datetime, \
         patch('os.path.expanduser', return_value=save_path), \
         patch('os.makedirs') as mock_makedirs, \
         patch.object(MagicMock(), 'save') as mock_save:
        
        mock_datetime.now.return_value.strftime.return_value = "20230101_123456"
        mock_screenshot.return_value.save = MagicMock()
        
        result = take_screenshot()
        mock_makedirs.assert_called_once_with("/screenshots", exist_ok=True)
        mock_screenshot.assert_called_once()
        mock_screenshot.return_value.save.assert_called_once_with(save_path)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_take_screenshot_success_specified_save_path():
    save_path = "/custom/path/screenshot.png"
    expected_output = f"Screenshot saved to {save_path}"
    
    with patch('dotenv.load_dotenv'), \
         patch('os.getenv', return_value=None), \
         patch('pyautogui.screenshot') as mock_screenshot, \
         patch('os.path.expanduser', return_value=save_path), \
         patch('os.makedirs') as mock_makedirs, \
         patch.object(MagicMock(), 'save') as mock_save:
        
        mock_screenshot.return_value.save = MagicMock()
        
        result = take_screenshot(save_path=save_path)
        mock_makedirs.assert_called_once_with("/custom/path", exist_ok=True)
        mock_screenshot.assert_called_once()
        mock_screenshot.return_value.save.assert_called_once_with(save_path)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_take_screenshot_missing_save_path():
    save_path = None
    expected_error = "SAVE_PATH is not set in environment variables."
    
    with patch('dotenv.load_dotenv'), \
         patch('os.getenv', return_value=None):
        
        result = take_screenshot(save_path)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "MISSING_SAVE_PATH"

@pytest.mark.asyncio
async def test_take_screenshot_exception():
    save_path = "/screenshots/screenshot.png"
    expected_error_code = "TAKE_SCREENSHOT_FAILED"
    expected_error_message = "Error taking screenshot: Sample exception."
    
    with patch('dotenv.load_dotenv'), \
         patch('os.getenv', return_value="/screenshots"), \
         patch('pyautogui.screenshot', side_effect=Exception("Sample exception.")), \
         patch('os.path.expanduser', return_value=save_path):
        
        result = take_screenshot()
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "TAKE_SCREENSHOT_FAILED"