import os
import pathspec

def read_gitignore(gitignore_path):
    with open(gitignore_path) as f:
        spec = f.read()
    return pathspec.PathSpec.from_lines('gitwildmatch', spec.splitlines())

def print_dir_tree(start_path: str, output_file, gitignore, prefix: str = '', max_depth=None, depth=0):
    base_name = os.path.basename(start_path)

    # Compute the relative path for gitignore matching.
    relative_path = os.path.relpath(start_path, project_root)

    # Check if this path should be ignored or is the .git directory.
    if gitignore.match_file(relative_path) or base_name == '.git':
        return

    # Stop if the maximum depth is reached.
    if max_depth is not None and depth > max_depth:
        return

    # Print the current path.
    print(prefix + '|-- ' + base_name, file=output_file)

    # If this is a directory, print its children.
    if os.path.isdir(start_path):
        for child in os.listdir(start_path):
            child_path = os.path.join(start_path, child)
            print_dir_tree(child_path, output_file, gitignore, prefix + '|   ', max_depth, depth+1)

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Read the .gitignore.
gitignore = read_gitignore(project_root + '/.gitignore')

# Print the directory tree.
with open(project_root + "/directory_tree.txt", "w") as f:
    print_dir_tree(project_root + "/src/aeiva", f, gitignore, max_depth=10)
