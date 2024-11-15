# tools/play_music/api.py

from typing import Dict, Any
import pygame
import threading
import os

# Initialize pygame mixer
pygame.mixer.init()
_lock = threading.Lock()

def play_music(file_path: str, loop: bool = False) -> Dict[str, Any]:
    """
    Plays a music file.

    Args:
        file_path (str): The path to the music file.
        loop (bool, optional): Whether to loop the music continuously. Defaults to False.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not file_path:
            return {
                "output": None,
                "error": "Music file path must be provided.",
                "error_code": "MISSING_FILE_PATH"
            }

        if not os.path.isfile(file_path):
            return {
                "output": None,
                "error": f"Music file not found: {file_path}",
                "error_code": "FILE_NOT_FOUND"
            }

        with _lock:
            try:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play(-1 if loop else 0)
                return {
                    "output": f"Playing music: {file_path}",
                    "error": None,
                    "error_code": "SUCCESS"
                }
            except Exception as e:
                return {
                    "output": None,
                    "error": f"Error playing music: {e}",
                    "error_code": "PLAY_MUSIC_FAILED"
                }
    except Exception as e:
        return {
            "output": None,
            "error": f"Unexpected error: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }