# toolkit/file_toolkit/pdf2text/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.file_toolkit.pdf2text.api import pdf2text
import os


class TestPdf2Text(unittest.TestCase):
    @patch('pdfplumber.open')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2text_success_return_text(self, mock_isfile, mock_pdfplumber_open):
        # Mock pdfplumber to return a PDF with two pages of text
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 text."
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 text."
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        response = pdf2text(
            input_file_path="sample.pdf",
            pages=None,
            output_file_path=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_pdfplumber_open.assert_called_once_with("sample.pdf")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        expected_text = "Page 1 text.\nPage 2 text.\n"
        self.assertEqual(response["output"]["text"], expected_text)

    @patch('pdfplumber.open')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2text_success_save_to_file(self, mock_isfile, mock_pdfplumber_open):
        # Mock pdfplumber to return a PDF with one page of text
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Single page text."
        mock_pdf.pages = [mock_page]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        with patch('builtins.open', mock_open := unittest.mock.mock_open()) as mock_file:
            response = pdf2text(
                input_file_path="sample.pdf",
                pages=None,
                output_file_path="output.txt"
            )

            # Assertions
            mock_isfile.assert_called_once_with("sample.pdf")
            mock_pdfplumber_open.assert_called_once_with("sample.pdf")
            mock_file.assert_called_once_with("output.txt", 'w', encoding='utf-8')
            mock_file().write.assert_called_once_with("Single page text.\n")
            self.assertEqual(response["error_code"], "SUCCESS")
            self.assertIsNone(response["error"])
            self.assertEqual(response["output"]["message"], "Text extracted and saved to 'output.txt'.")

    @patch('os.path.isfile', return_value=False)
    def test_pdf2text_file_not_found(self, mock_isfile):
        response = pdf2text(
            input_file_path="nonexistent.pdf",
            pages=None,
            output_file_path=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("nonexistent.pdf")
        self.assertEqual(response["error_code"], "FILE_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("Input file 'nonexistent.pdf' does not exist.", response["error"])

    @patch('pdfplumber.open', side_effect=IOError("Failed to open PDF"))
    @patch('os.path.isfile', return_value=True)
    def test_pdf2text_io_error_during_open(self, mock_isfile, mock_pdfplumber_open):
        response = pdf2text(
            input_file_path="corrupted.pdf",
            pages=None,
            output_file_path=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("corrupted.pdf")
        mock_pdfplumber_open.assert_called_once_with("corrupted.pdf")
        self.assertEqual(response["error_code"], "IO_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("IO_ERROR: Failed to open PDF", response["error"])

    @patch('pdfplumber.open')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2text_unexpected_error(self, mock_isfile, mock_pdfplumber_open):
        # Mock pdfplumber to raise an unexpected exception
        mock_pdfplumber_open.side_effect = Exception("Unexpected exception")

        response = pdf2text(
            input_file_path="sample.pdf",
            pages=None,
            output_file_path=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_pdfplumber_open.assert_called_once_with("sample.pdf")
        self.assertEqual(response["error_code"], "UNEXPECTED_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("UNEXPECTED_ERROR: Unexpected exception", response["error"])

    def test_pdf2text_validation_error_missing_params(self):
        # Missing required 'input_file_path' parameter
        with self.assertRaises(TypeError):
            pdf2text(
                input_file_path=None,  # Invalid input
                pages=None,
                output_file_path=None
            )

    @patch('pdfplumber.open')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2text_empty_pages_list(self, mock_isfile, mock_pdfplumber_open):
        # Mock pdfplumber to return a PDF with three pages
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 text."
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 text."
        mock_page3 = MagicMock()
        mock_page3.extract_text.return_value = "Page 3 text."
        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        response = pdf2text(
            input_file_path="sample.pdf",
            pages=[],
            output_file_path=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_pdfplumber_open.assert_called_once_with("sample.pdf")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        # Since pages list is empty, no pages are extracted, resulting in empty text
        self.assertEqual(response["output"]["text"], "")


if __name__ == "__main__":
    unittest.main()