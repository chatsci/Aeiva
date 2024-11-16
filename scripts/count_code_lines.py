import os
import argparse


def count_code_lines(path: str) -> int:
    """
    Count the number of lines in Python files (.py) in the given directory and subdirectories.

    Args:
        path (str): The directory to search for .py files.

    Returns:
        int: The total number of lines in all .py files.
    """
    total_lines = 0

    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        line_count = len(lines)
                        print(f"{file_path}: {line_count} lines")
                        total_lines += line_count
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

    return total_lines


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate the number of lines in Python files (.py) in a directory."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=os.getcwd(),
        help="The directory to search for .py files (default: current directory).",
    )
    args = parser.parse_args()

    path = args.path
    if not os.path.exists(path):
        print(f"Error: The specified path does not exist: {path}")
    else:
        print(f"Calculating lines of code in Python files under: {path}")
        total = count_code_lines(path)
        print(f"\nTotal lines of Python code: {total}")