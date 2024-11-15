# toolkit/system_toolkit.py

from aeiva.tool.toolkit.toolkit import Toolkit

class SystemToolkit(Toolkit):
    """
    A toolkit for interacting with system-level operations.
    """

    def __init__(self, config=None):
        super().__init__(
            name="SystemToolkit",
            tool_names=[
                "get_system_info",
                "open_application",
                "close_application",
                "percept_terminal_input",
                "play_music",
                "stop_music",
                "take_screenshot"
            ],
            config=config
        )