# toolkit/auto_ui_toolkit.py

from aeiva.tool.toolkit.toolkit import Toolkit

class AutoUIToolkit(Toolkit):
    """
    A toolkit for automating GUI interactions.
    """

    def __init__(self, config=None):
        super().__init__(
            name="AutoUIToolkit",
            tool_names=[
                "analyze_gui",
                "analyze_gui_by_ocr",
                "click_mouse",
                "click_on_element",
                "move_mouse",
                "operate_computer",
                "scroll",
                "type_into_element",
                "type_keyboard"
            ],
            config=config
        )