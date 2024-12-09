"""
This script will print the requirements.txt file for the project.
The output file will be saved in the project's root directory.
"""
import os
import subprocess


current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
cmd = f"pipreqs --force {project_dir}"
subprocess.run(cmd, shell=True)
