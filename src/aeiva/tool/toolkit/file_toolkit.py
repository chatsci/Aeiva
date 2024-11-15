# toolkit/file_toolkit.py

from aeiva.tool.toolkit.toolkit import Toolkit

class FileToolkit(Toolkit):
    """
    A toolkit for file-related operations.
    """

    def __init__(self, config=None):
        super().__init__(
            name="FileToolkit",
            tool_names=[
                "create_file_or_folder",
                "delete_file",
                "edit_file",
                "find_file",
                "list_files",
                "open_file_or_folder",
                "read_file",
                "rename_file",
                "search_file_or_folder",
                "write_file"
            ],
            config=config
        )