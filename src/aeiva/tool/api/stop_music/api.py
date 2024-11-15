# tools/stop_music/api.py

from typing import Dict, Any
import pygame
import threading

_lock = threading.Lock()

def stop_music() -> Dict[str, Any]:
    """
    Stops playing music.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        with _lock:
            try:
                pygame.mixer.music.stop()
                return {
                    "output": "Music stopped.",
                    "error": None,
                    "error_code": "SUCCESS"
                }
            except Exception as e:
                return {
                    "output": None,
                    "error": f"Error stopping music: {e}",
                    "error_code": "STOP_MUSIC_FAILED"
                }
    except Exception as e:
        return {
            "output": None,
            "error": f"Unexpected error: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }