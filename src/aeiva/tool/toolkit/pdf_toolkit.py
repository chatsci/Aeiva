# toolkit/pdf_toolkit.py

from aeiva.tool.toolkit.toolkit import Toolkit

class PdfToolkit(Toolkit):
    """
    A toolkit for interacting with PDF files.
    """

    def __init__(self, config=None):
        super().__init__(
            name="PdfToolkit",
            tool_names=[
                "pdf2markdown",
                "pdf2text",
                "pdf2tables",
                "pdf2images",
                "pdf2metadata",
                "pdf2ocr"
            ],
            config=config
        )