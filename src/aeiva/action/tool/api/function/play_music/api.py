# tools/play_music/api.py

import pygame
import threading
import os

# Initialize pygame mixer
pygame.mixer.init()
_lock = threading.Lock()

def play_music(file_path: str, loop: bool = False) -> str:
    """
    Play a music file.

    Args:
        file_path (str): The path to the music file.
        loop (bool): Whether to loop the music continuously.

    Returns:
        str: A message indicating the result.
    """
    if not os.path.isfile(file_path):
        return f"Music file not found: {file_path}"

    with _lock:
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play(-1 if loop else 0)
            return f"Playing music: {file_path}"
        except Exception as e:
            return f"Error playing music: {e}"