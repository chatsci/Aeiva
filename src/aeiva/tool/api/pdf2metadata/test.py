# toolkit/file_toolkit/pdf2metadata/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.file_toolkit.pdf2metadata.api import pdf2metadata
import os


class TestPdf2Metadata(unittest.TestCase):
    @patch('pypdf.PdfReader')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2metadata_success(self, mock_isfile, mock_pdfreader):
        # Mock PdfReader and its metadata
        mock_reader = MagicMock()
        mock_reader.metadata = {
            "/Title": "Sample PDF",
            "/Author": "John Doe",
            "/Subject": "Testing",
            "/Creator": "PyPDF2",
            "/Producer": "PyPDF2",
            "/CreationDate": "D:20230101120000",
            "/ModDate": "D:20230102120000"
        }
        mock_pdfreader.return_value = mock_reader

        response = pdf2metadata(
            input_file_path="sample.pdf"
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_pdfreader.assert_called_once_with("sample.pdf")
        expected_metadata = {
            "Title": "Sample PDF",
            "Author": "John Doe",
            "Subject": "Testing",
            "Creator": "PyPDF2",
            "Producer": "PyPDF2",
            "CreationDate": "D:20230101120000",
            "ModDate": "D:20230102120000"
        }
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        self.assertEqual(response["output"]["metadata"], expected_metadata)

    @patch('os.path.isfile', return_value=False)
    def test_pdf2metadata_file_not_found(self, mock_isfile):
        response = pdf2metadata(
            input_file_path="nonexistent.pdf"
        )

        # Assertions
        mock_isfile.assert_called_once_with("nonexistent.pdf")
        self.assertEqual(response["error_code"], "FILE_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("Input file 'nonexistent.pdf' does not exist.", response["error"])

    @patch('pypdf.PdfReader', side_effect=IOError("Failed to read PDF"))
    @patch('os.path.isfile', return_value=True)
    def test_pdf2metadata_io_error(self, mock_isfile, mock_pdfreader):
        response = pdf2metadata(
            input_file_path="corrupted.pdf"
        )

        # Assertions
        mock_isfile.assert_called_once_with("corrupted.pdf")
        mock_pdfreader.assert_called_once_with("corrupted.pdf")
        self.assertEqual(response["error_code"], "IO_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("IO_ERROR: Failed to read PDF", response["error"])

    @patch('pypdf.PdfReader', side_effect=Exception("Unexpected exception"))
    @patch('os.path.isfile', return_value=True)
    def test_pdf2metadata_unexpected_error(self, mock_isfile, mock_pdfreader):
        response = pdf2metadata(
            input_file_path="sample.pdf"
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_pdfreader.assert_called_once_with("sample.pdf")
        self.assertEqual(response["error_code"], "UNEXPECTED_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("UNEXPECTED_ERROR: Unexpected exception", response["error"])


if __name__ == "__main__":
    unittest.main()