import os
import shutil


def remove_pycache(directory):
    for root, dirs, files in os.walk(directory):
        for dir in dirs:
            if dir == "__pycache__":
                full_path = os.path.join(root, dir)
                print(f"Removing {full_path}")
                shutil.rmtree(full_path)


project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
remove_pycache(project_root)
