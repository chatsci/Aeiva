import os


def is_video_file(filepath: str) -> bool:
    video_file_extensions = ['.mp4', '.avi', '.mov', '.flv', '.mkv', '.wmv']
    _, extension = os.path.splitext(filepath)
    is_video = extension.lower() in video_file_extensions
    return is_video
