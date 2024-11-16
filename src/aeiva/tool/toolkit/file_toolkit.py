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
                "open_file_or_folder",
                "search_file_or_folder",
                "copy_file_or_folder",
                "move_file_or_folder",
                "change_permissions",
                "get_file_metadata",
                "delete_file",
                "edit_file",
                "find_file",
                "list_files",
                "read_file",
                "rename_file",
                "write_file"
            ],
            config=config
        )