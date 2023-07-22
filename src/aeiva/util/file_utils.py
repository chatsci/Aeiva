import os
import shutil
import torch


def ensure_dir(file_path):
    """
    Check if a directory of the given file path exists, if not, create it.

    Args:
    file_path (str): The path of the file.

    Returns:
    dir_path (str): The directory path.
    """

    # Get directory name from file path
    dir_path = os.path.dirname(file_path)

    # If directory does not exist, create it
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"Directory {dir_path} created")
    else:
        print(f"Directory {dir_path} already exists")

    return dir_path


def copy_file_to_dst(input_file, dst_folder):
    if os.path.isfile(input_file):
        # Ensure the destination directory exists
        os.makedirs(dst_folder, exist_ok=True)
        # Construct destination file path
        dst_file = os.path.join(dst_folder, os.path.basename(input_file))
        shutil.copy(input_file, dst_file)
        print(f"Copied {input_file} to {dst_folder}.")
    else:
        print(f"File {input_file} does not exist.")


def print_dict_to_file(d, outputfile):
    result = "{\n"
    for key, value in d.items():
        if isinstance(value, dict):
            result += f"  {key} : {tensor_dict_to_str(value)},\n"
        elif torch.is_tensor(value):
            result += f"  {key} : {value.tolist()},\n"  # convert tensor to list
        else:
            result += f"  {key} : {value},\n"
    result += "}"
    with open(outputfile, 'w') as f:
        f.write(result)
    return result
