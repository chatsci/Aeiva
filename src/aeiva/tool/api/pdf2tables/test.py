# toolkit/file_toolkit/pdf2tables/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.file_toolkit.pdf2tables.api import pdf2tables
import os
import pandas as pd


class TestPdf2Tables(unittest.TestCase):
    @patch('pdfplumber.open')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2tables_success_return_tables_json(self, mock_isfile, mock_pdfplumber_open):
        # Mock pdfplumber to return a PDF with one page containing two tables
        mock_pdf = MagicMock()
        mock_page = MagicMock()

        # Mock extract_tables to return two tables
        mock_page.extract_tables.return_value = [
            [["Header1", "Header2"], ["Row1Col1", "Row1Col2"]],
            [["H1", "H2", "H3"], ["R1C1", "R1C2", "R1C3"]]
        ]

        mock_pdf.pages = [mock_page]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        response = pdf2tables(
            input_file_path="sample.pdf",
            pages=[0],
            output_format="json",
            output_file_path=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_pdfplumber_open.assert_called_once_with("sample.pdf")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        expected_tables = [
            {"Header1": "Row1Col1", "Header2": "Row1Col2"},
            {"H1": "R1C1", "H2": "R1C2", "H3": "R1C3"}
        ]
        self.assertEqual(response["output"]["tables"], expected_tables)

    @patch('pdfplumber.open')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2tables_success_save_to_json(self, mock_isfile, mock_pdfplumber_open):
        # Mock pdfplumber to return a PDF with one page containing one table
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_tables.return_value = [
            [["Name", "Age"], ["Alice", "30"], ["Bob", "25"]]
        ]
        mock_pdf.pages = [mock_page]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        with patch('builtins.open', mock_open := unittest.mock.mock_open()) as mock_file:
            response = pdf2tables(
                input_file_path="sample.pdf",
                pages=[0],
                output_format="json",
                output_file_path="tables.json"
            )

            # Assertions
            mock_isfile.assert_called_once_with("sample.pdf")
            mock_pdfplumber_open.assert_called_once_with("sample.pdf")
            mock_file.assert_called_once_with("tables.json", 'w', encoding='utf-8')
            expected_tables = [
                {"Name": "Alice", "Age": "30"},
                {"Name": "Bob", "Age": "25"}
            ]
            mock_file().write.assert_called_once()
            written_content = mock_open().write.call_args[0][0]
            self.assertIn('"Name": "Alice"', written_content)
            self.assertIn('"Age": "25"', written_content)
            self.assertEqual(response["error_code"], "SUCCESS")
            self.assertIsNone(response["error"])
            self.assertEqual(response["output"]["message"], "Tables extracted and saved to 'tables.json' in JSON format.")

    @patch('pdfplumber.open')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2tables_success_save_to_csv(self, mock_isfile, mock_pdfplumber_open):
        # Mock pdfplumber to return a PDF with two pages containing one table each
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_tables.return_value = [
            [["Product", "Price"], ["Book", "12.99"], ["Pen", "1.99"]]
        ]
        mock_page2 = MagicMock()
        mock_page2.extract_tables.return_value = [
            [["Service", "Cost"], ["Cleaning", "25.00"], ["Repair", "40.00"]]
        ]
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        with patch('builtins.open', mock_open := unittest.mock.mock_open()) as mock_file, \
             patch('pandas.concat') as mock_concat:
            # Mock pandas.concat to return a combined DataFrame
            mock_combined_df = MagicMock()
            mock_combined_df.to_csv.return_value = None
            mock_concat.return_value = mock_combined_df

            response = pdf2tables(
                input_file_path="sample.pdf",
                pages=[0, 1],
                output_format="csv",
                output_file_path="tables.csv"
            )

            # Assertions
            mock_isfile.assert_called_once_with("sample.pdf")
            mock_pdfplumber_open.assert_called_once_with("sample.pdf")
            mock_concat.assert_called_once()
            mock_combined_df.to_csv.assert_called_once_with("tables.csv", index=False, encoding='utf-8')
            self.assertEqual(response["error_code"], "SUCCESS")
            self.assertIsNone(response["error"])
            self.assertEqual(response["output"]["message"], "Tables extracted and saved to 'tables.csv' in CSV format.")

    @patch('pdfplumber.open')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2tables_file_not_found(self, mock_isfile, mock_pdfplumber_open):
        response = pdf2tables(
            input_file_path="nonexistent.pdf",
            pages=None,
            output_format="json",
            output_file_path=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("nonexistent.pdf")
        mock_pdfplumber_open.assert_not_called()
        self.assertEqual(response["error_code"], "FILE_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("Input file 'nonexistent.pdf' does not exist.", response["error"])

    @patch('pdfplumber.open')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2tables_table_extraction_error(self, mock_isfile, mock_pdfplumber_open):
        # Mock pdfplumber to raise an exception during table extraction
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_tables.side_effect = Exception("Failed to extract tables")
        mock_pdf.pages = [mock_page]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        response = pdf2tables(
            input_file_path="sample.pdf",
            pages=[0],
            output_format="json",
            output_file_path=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_pdfplumber_open.assert_called_once_with("sample.pdf")
        self.assertEqual(response["error_code"], "TABLE_EXTRACTION_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("TABLE_EXTRACTION_ERROR: Failed to extract tables", response["error"])

    @patch('pdfplumber.open', side_effect=Exception("Unexpected exception"))
    @patch('os.path.isfile', return_value=True)
    def test_pdf2tables_unexpected_error(self, mock_isfile, mock_pdfplumber_open):
        response = pdf2tables(
            input_file_path="sample.pdf",
            pages=None,
            output_format="json",
            output_file_path=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_pdfplumber_open.assert_called_once_with("sample.pdf")
        self.assertEqual(response["error_code"], "UNEXPECTED_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("UNEXPECTED_ERROR: Unexpected exception", response["error"])

    def test_pdf2tables_validation_error_invalid_format(self):
        response = pdf2tables(
            input_file_path="sample.pdf",
            pages=None,
            output_format="xml",  # Invalid format
            output_file_path=None
        )

        # Assertions
        self.assertEqual(response["error_code"], "VALIDATION_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("Invalid output format 'xml'", response["error"])


if __name__ == "__main__":
    unittest.main()