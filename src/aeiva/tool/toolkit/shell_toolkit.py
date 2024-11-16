# toolkit/shell_toolkit.py

from aeiva.tool.toolkit.toolkit import Toolkit

class ShellToolkit(Toolkit):
    """
    A toolkit for shell and terminal operations.
    """

    def __init__(self, config=None):
        super().__init__(
            name="ShellToolkit",
            tool_names=[
                "chwdir",
                "execute_bash_command",
                "execute_script",
                "grep",
                "create_new_shell_session"
            ],
            config=config
        )