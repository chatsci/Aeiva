# tools/stop_music/test.py

import pytest
from unittest.mock import patch
from .api import stop_music

@pytest.mark.asyncio
async def test_stop_music_success():
    expected_output = "Music stopped."
    
    with patch('pygame.mixer.music.stop') as mock_stop:
        result = stop_music()
        mock_stop.assert_called_once()
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_stop_music_failed():
    expected_error_code = "STOP_MUSIC_FAILED"
    expected_error_message = "Error stopping music: Sample exception."
    
    with patch('pygame.mixer.music.stop', side_effect=Exception("Sample exception.")):
        result = stop_music()
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == expected_error_code

@pytest.mark.asyncio
async def test_stop_music_unexpected_error():
    expected_error_code = "UNEXPECTED_ERROR"
    expected_error_message = "Unexpected error: Sample exception."
    
    with patch('pygame.mixer.music.stop', side_effect=Exception("Sample exception.")), \
         patch('threading.Lock.__enter__', side_effect=Exception("Sample exception.")):
        result = stop_music()
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == expected_error_code