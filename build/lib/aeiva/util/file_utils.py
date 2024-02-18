import os
import shutil


def ensure_dir(file_path):
    dir_path = os.path.dirname(file_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"Directory {dir_path} created")
    else:
        print(f"Directory {dir_path} already exists")

    return dir_path


def copy_file_to_dst(input_file, dst_folder):
    if os.path.isfile(input_file):
        os.makedirs(dst_folder, exist_ok=True)
        dst_file = os.path.join(dst_folder, os.path.basename(input_file))
        if os.path.exists(dst_file):
            print(f"File {dst_file} already exists.")  # do not overwrite
            return

        shutil.copy(input_file, dst_file)
        print(f"Copied {input_file} to {dst_folder}.")
    else:
        print(f"File {input_file} does not exist.")


def is_video_file(filepath: str) -> bool:
    video_file_extensions = ['.mp4', '.avi', '.mov', '.flv', '.mkv', '.wmv']
    _, extension = os.path.splitext(filepath)
    is_video = extension.lower() in video_file_extensions
    return is_video


def is_audio_file(filepath: str) -> bool:
    audio_file_extensions = ['.mp3', '.wav', '.flac', '.ogg', '.m4a']
    _, extension = os.path.splitext(filepath)
    is_audio = extension.lower() in audio_file_extensions
    return is_audio


def is_image_file(filepath: str) -> bool:
    image_file_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
    _, extension = os.path.splitext(filepath)
    is_image = extension.lower() in image_file_extensions
    return is_image
