# toolkit/arxiv_toolkit.py

from aeiva.tool.toolkit.toolkit import Toolkit

class ArxivToolkit(Toolkit):
    """
    A toolkit for interacting with the arXiv API.
    """

    def __init__(self, config=None):
        super().__init__(
            name="ArxivToolkit",
            tool_names=[
                "download_arxiv_papers",
                "search_arxiv_papers"
            ],
            config=config
        )