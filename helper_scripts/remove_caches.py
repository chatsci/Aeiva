"""
This script removes all cache and log directories from the project.
"""
import os
import shutil


def remove_cache_dirs(directory, dirs_to_remove):
    for root, dirs, files in os.walk(directory):
        for dir in dirs:
            if dir in dirs_to_remove:
                full_path = os.path.join(root, dir)
                print(f"Removing {full_path}")
                shutil.rmtree(full_path)

# remove cache and log dirs, including the dir themselves.
dirs_to_remove = ["__pycache__", "lightning_logs"]
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
remove_cache_dirs(project_root, dirs_to_remove)


def remove_dir_contents(dirs):
    for folder_path in dirs:
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')


# remove cache and log dir contents, keeping the dirs themselves.
dirs = [
    project_root + "/outputs/cache/",
]
remove_dir_contents(dirs)
