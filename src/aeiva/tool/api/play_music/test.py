# tools/play_music/test.py

import pytest
from unittest.mock import patch, MagicMock
from .api import play_music
import os

@pytest.mark.asyncio
async def test_play_music_success():
    file_path = "/path/to/music.mp3"
    loop = True
    expected_output = f"Playing music: {file_path}"
    
    with patch('os.path.isfile', return_value=True), \
         patch('pygame.mixer.music.load') as mock_load, \
         patch('pygame.mixer.music.play') as mock_play:
        
        result = play_music(file_path, loop)
        mock_load.assert_called_once_with(file_path)
        mock_play.assert_called_once_with(-1)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_play_music_success_no_loop():
    file_path = "/path/to/music.mp3"
    loop = False
    expected_output = f"Playing music: {file_path}"
    
    with patch('os.path.isfile', return_value=True), \
         patch('pygame.mixer.music.load') as mock_load, \
         patch('pygame.mixer.music.play') as mock_play:
        
        result = play_music(file_path, loop)
        mock_load.assert_called_once_with(file_path)
        mock_play.assert_called_once_with(0)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_play_music_missing_file_path():
    file_path = ""
    loop = False
    expected_error = "Music file path must be provided."
    
    result = play_music(file_path, loop)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "MISSING_FILE_PATH"

@pytest.mark.asyncio
async def test_play_music_file_not_found():
    file_path = "/path/to/nonexistent_music.mp3"
    loop = False
    expected_error = f"Music file not found: {file_path}"
    
    with patch('os.path.isfile', return_value=False):
        result = play_music(file_path, loop)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "FILE_NOT_FOUND"

@pytest.mark.asyncio
async def test_play_music_play_failed():
    file_path = "/path/to/music.mp3"
    loop = False
    expected_error_code = "PLAY_MUSIC_FAILED"
    expected_error_message = "Error playing music: Sample exception."
    
    with patch('os.path.isfile', return_value=True), \
         patch('pygame.mixer.music.load'), \
         patch('pygame.mixer.music.play', side_effect=Exception("Sample exception.")):
        
        result = play_music(file_path, loop)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == expected_error_code

@pytest.mark.asyncio
async def test_play_music_unexpected_error():
    file_path = "/path/to/music.mp3"
    loop = False
    expected_error_code = "UNEXPECTED_ERROR"
    expected_error_message = "Unexpected error: Sample exception."
    
    with patch('os.path.isfile', side_effect=Exception("Sample exception.")):
        result = play_music(file_path, loop)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "UNEXPECTED_ERROR"