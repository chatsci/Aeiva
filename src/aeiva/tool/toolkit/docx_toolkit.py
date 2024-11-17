# toolkit/pdf_toolkit.py

from aeiva.tool.toolkit.toolkit import Toolkit

class DocxToolkit(Toolkit):
    """
    A toolkit for interacting with Docx files.
    """

    def __init__(self, config=None):
        super().__init__(
            name="DocxToolkit",
            tool_names=[
                "create_docx",
                "docx2html",
                "docx2images",
                "docx2markdown",
                "docx2metadata",
                "docx2pdf",
                "docx2text",
                "modify_docx"
            ],
            config=config
        )