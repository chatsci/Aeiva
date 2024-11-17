# toolkit/file_toolkit/extract_file_as_markdown/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.file_toolkit.extract_file_as_markdown.api import (
    pdf2markdown
)
import os

# Import WebDriverException if used in api.py
from selenium.common.exceptions import WebDriverException


class TestPdf2Markdown(unittest.TestCase):
    @patch('pymupdf4llm.to_markdown')
    @patch('builtins.open')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2markdown_success_return_markdown(self, mock_isfile, mock_open, mock_to_markdown):
        # Mock the to_markdown function to return sample markdown
        mock_to_markdown.return_value = "# Sample Markdown"

        response = pdf2markdown(
            input_file_path="sample.pdf",
            pages=None,
            output_file_path=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_to_markdown.assert_called_once_with("sample.pdf", None)
        mock_open.assert_not_called()

        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        self.assertEqual(response["output"]["markdown"], "# Sample Markdown")

    @patch('pymupdf4llm.to_markdown')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('os.path.isfile', return_value=True)
    def test_pdf2markdown_success_save_to_file(self, mock_isfile, mock_open, mock_to_markdown):
        # Mock the to_markdown function to return sample markdown
        mock_to_markdown.return_value = "# Sample Markdown"

        response = pdf2markdown(
            input_file_path="sample.pdf",
            pages=[0, 1],
            output_file_path="output.md"
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_to_markdown.assert_called_once_with("sample.pdf", [0, 1])
        mock_open.assert_called_once_with("output.md", 'w', encoding='utf-8')
        mock_open().write.assert_called_once_with("# Sample Markdown")

        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        self.assertEqual(response["output"]["message"], "Markdown file saved to 'output.md'.")

    @patch('os.path.isfile', return_value=False)
    def test_pdf2markdown_file_not_found(self, mock_isfile):
        response = pdf2markdown(
            input_file_path="nonexistent.pdf",
            pages=None,
            output_file_path=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("nonexistent.pdf")

        self.assertEqual(response["error_code"], "FILE_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("Input file 'nonexistent.pdf' does not exist.", response["error"])

    @patch('pymupdf4llm.to_markdown', side_effect=Exception("JavaScript Error"))
    @patch('os.path.isfile', return_value=True)
    def test_pdf2markdown_js_execution_error(self, mock_isfile, mock_to_markdown):
        response = pdf2markdown(
            input_file_path="sample.pdf",
            pages=None,
            output_file_path=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_to_markdown.assert_called_once_with("sample.pdf", None)

        self.assertEqual(response["error_code"], "JS_EXECUTION_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("JS_EXECUTION_ERROR: JavaScript Error", response["error"])

    @patch('builtins.open', side_effect=IOError("Failed to write file"))
    @patch('pymupdf4llm.to_markdown')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2markdown_io_error(self, mock_isfile, mock_to_markdown, mock_open):
        # Mock the to_markdown function to return sample markdown
        mock_to_markdown.return_value = "# Sample Markdown"

        response = pdf2markdown(
            input_file_path="sample.pdf",
            pages=[0],
            output_file_path="output.md"
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_to_markdown.assert_called_once_with("sample.pdf", [0])
        mock_open.assert_called_once_with("output.md", 'w', encoding='utf-8')

        self.assertEqual(response["error_code"], "IO_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("IO_ERROR: Failed to write file", response["error"])

    @patch('pymupdf4llm.to_markdown', side_effect=WebDriverException("WebDriver failed"))
    @patch('os.path.isfile', return_value=True)
    def test_pdf2markdown_webdriver_error(self, mock_isfile, mock_to_markdown):
        response = pdf2markdown(
            input_file_path="sample.pdf",
            pages=None,
            output_file_path=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_to_markdown.assert_called_once_with("sample.pdf", None)

        self.assertEqual(response["error_code"], "JS_EXECUTION_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("JS_EXECUTION_ERROR: WebDriver failed", response["error"])

    @patch('pymupdf4llm.to_markdown', side_effect=Exception("Unexpected Error"))
    @patch('os.path.isfile', return_value=True)
    def test_pdf2markdown_unexpected_error(self, mock_isfile, mock_to_markdown):
        response = pdf2markdown(
            input_file_path="sample.pdf",
            pages=None,
            output_file_path=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_to_markdown.assert_called_once_with("sample.pdf", None)

        self.assertEqual(response["error_code"], "UNEXPECTED_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("UNEXPECTED_ERROR: Unexpected Error", response["error"])

    def test_pdf2markdown_validation_error_missing_params(self):
        # Missing required 'input_file_path' parameter
        with self.assertRaises(TypeError):
            # This should raise a TypeError before even entering the function
            pdf2markdown(
                input_file_path=None,  # Invalid input
                pages=None,
                output_file_path=None
            )

    @patch('pymupdf4llm.to_markdown')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('os.path.isfile', return_value=True)
    def test_pdf2markdown_empty_pages_list(self, mock_isfile, mock_open, mock_to_markdown):
        # Mock the to_markdown function to return sample markdown
        mock_to_markdown.return_value = "# All Pages Markdown"

        response = pdf2markdown(
            input_file_path="sample.pdf",
            pages=[],
            output_file_path=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_to_markdown.assert_called_once_with("sample.pdf", [])
        mock_open.assert_not_called()

        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        self.assertEqual(response["output"]["markdown"], "# All Pages Markdown")


if __name__ == "__main__":
    unittest.main()