# tools/stop_music/api.py

import pygame
import threading

_lock = threading.Lock()

def stop_music() -> str:
    """
    Stop playing music.

    Returns:
        str: A message indicating the result.
    """
    with _lock:
        try:
            pygame.mixer.music.stop()
            return "Music stopped."
        except Exception as e:
            return f"Error stopping music: {e}"