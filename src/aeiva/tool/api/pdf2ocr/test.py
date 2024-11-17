# toolkit/file_toolkit/pdf2ocr/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.file_toolkit.pdf2ocr.api import pdf2ocr
import os


class TestPdf2Ocr(unittest.TestCase):
    @patch('ocrmypdf.ocr')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2ocr_success_save_pdf(self, mock_isfile, mock_ocr):
        response = pdf2ocr(
            input_file_path="sample.pdf",
            output_file_path="ocr_output.pdf",
            language="eng"
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_ocr.assert_called_once_with("sample.pdf", "ocr_output.pdf", language="eng", force_ocr=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        self.assertEqual(response["output"]["message"], "OCR completed and saved to 'ocr_output.pdf'.")

    @patch('ocrmypdf.ocr')
    @patch('pypdf.PdfReader')
    @patch('os.path.isfile', return_value=True)
    @patch('os.remove')
    def test_pdf2ocr_success_return_text(self, mock_remove, mock_isfile, mock_pdfreader, mock_ocr):
        # Mock OCR to perform successfully
        mock_ocr.return_value = None
        # Mock PdfReader and its text extraction
        mock_reader = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Extracted OCR text."
        mock_reader.pages = [mock_page]
        mock_pdfreader.return_value = mock_reader

        response = pdf2ocr(
            input_file_path="sample.pdf",
            output_file_path=None,
            language="eng"
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_ocr.assert_called_once_with("sample.pdf", "temp_ocr.pdf", language="eng", force_ocr=True)
        mock_pdfreader.assert_called_once_with("temp_ocr.pdf")
        mock_remove.assert_called_once_with("temp_ocr.pdf")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        self.assertEqual(response["output"]["text"], "Extracted OCR text.\n")

    @patch('os.path.isfile', return_value=False)
    def test_pdf2ocr_file_not_found(self, mock_isfile):
        response = pdf2ocr(
            input_file_path="nonexistent.pdf",
            output_file_path=None,
            language="eng"
        )

        # Assertions
        mock_isfile.assert_called_once_with("nonexistent.pdf")
        self.assertEqual(response["error_code"], "FILE_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("Input file 'nonexistent.pdf' does not exist.", response["error"])

    @patch('ocrmypdf.ocr', side_effect=ocrmypdf.exceptions.OCRError("OCR failed"))
    @patch('os.path.isfile', return_value=True)
    def test_pdf2ocr_ocr_error(self, mock_isfile, mock_ocr):
        response = pdf2ocr(
            input_file_path="sample.pdf",
            output_file_path="ocr_output.pdf",
            language="eng"
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_ocr.assert_called_once_with("sample.pdf", "ocr_output.pdf", language="eng", force_ocr=True)
        self.assertEqual(response["error_code"], "OCR_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("OCR_ERROR: OCR failed", response["error"])

    @patch('ocrmypdf.ocr', side_effect=IOError("Failed to write file"))
    @patch('os.path.isfile', return_value=True)
    def test_pdf2ocr_io_error(self, mock_isfile, mock_ocr):
        response = pdf2ocr(
            input_file_path="sample.pdf",
            output_file_path="ocr_output.pdf",
            language="eng"
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_ocr.assert_called_once_with("sample.pdf", "ocr_output.pdf", language="eng", force_ocr=True)
        self.assertEqual(response["error_code"], "IO_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("IO_ERROR: Failed to write file", response["error"])

    @patch('ocrmypdf.ocr', side_effect=Exception("Unexpected exception"))
    @patch('os.path.isfile', return_value=True)
    def test_pdf2ocr_unexpected_error(self, mock_isfile, mock_ocr):
        response = pdf2ocr(
            input_file_path="sample.pdf",
            output_file_path=None,
            language="eng"
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_ocr.assert_called_once_with("sample.pdf", "temp_ocr.pdf", language="eng", force_ocr=True)
        self.assertEqual(response["error_code"], "UNEXPECTED_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("UNEXPECTED_ERROR: Unexpected exception", response["error"])

    def test_pdf2ocr_validation_error_invalid_language(self):
        response = pdf2ocr(
            input_file_path="sample.pdf",
            output_file_path=None,
            language=""  # Invalid language
        )

        # Assertions
        self.assertEqual(response["error_code"], "VALIDATION_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("Invalid language parameter", response["error"])


if __name__ == "__main__":
    unittest.main()