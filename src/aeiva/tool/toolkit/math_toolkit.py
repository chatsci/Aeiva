# toolkit/math_toolkit.py

from aeiva.tool.toolkit.toolkit import Toolkit

class MathToolkit(Toolkit):
    """
    A toolkit for mathematical operations.
    """

    def __init__(self, config=None):
        super().__init__(
            name="MathToolkit",
            tool_names=["calculator"],
            config=config
        )