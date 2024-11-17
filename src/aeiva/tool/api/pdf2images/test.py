# toolkit/file_toolkit/pdf2images/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.file_toolkit.pdf2images.api import pdf2images
import os
from PIL import Image
import io


class TestPdf2Images(unittest.TestCase):
    @patch('pdfplumber.open')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2images_success_return_images(self, mock_isfile, mock_pdfplumber_open):
        # Mock pdfplumber to return a PDF with one page containing two images
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.images = [
            {'x0': 100, 'top': 100, 'x1': 200, 'bottom': 200},
            {'x0': 300, 'top': 300, 'x1': 400, 'bottom': 400}
        ]
        mock_pdf.pages = [mock_page]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        # Mock the image extraction and PIL.Image.open
        with patch('pdfplumber.page.Page.crop') as mock_crop, \
             patch('pdfplumber.page.Page.to_image') as mock_to_image, \
             patch('PIL.Image.open') as mock_image_open:
            # Create a dummy image
            dummy_image = MagicMock(spec=Image.Image)
            dummy_image.save.return_value = None
            mock_image_open.return_value = dummy_image

            # Mock cropped_image.original to return fake image bytes
            mock_crop.return_value.to_image.return_value.original = b'fake_image_bytes'

            response = pdf2images(
                input_file_path="sample.pdf",
                pages=[0],
                output_format="png",
                output_directory=None
            )

            # Assertions
            mock_isfile.assert_called_once_with("sample.pdf")
            mock_pdfplumber_open.assert_called_once_with("sample.pdf")
            self.assertEqual(response["error_code"], "SUCCESS")
            self.assertIsNone(response["error"])
            self.assertEqual(len(response["output"]["images"]), 2)
            self.assertEqual(response["output"]["images"][0]["page"], 0)
            self.assertEqual(response["output"]["images"][0]["image"], 'fake_image_bytes'.decode('latin1'))

    @patch('pdfplumber.open')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2images_success_save_to_directory_png(self, mock_isfile, mock_pdfplumber_open):
        # Mock pdfplumber to return a PDF with one page containing one image
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.images = [
            {'x0': 150, 'top': 150, 'x1': 250, 'bottom': 250}
        ]
        mock_pdf.pages = [mock_page]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        with patch('builtins.open', unittest.mock.mock_open()) as mock_file, \
             patch('PIL.Image.open') as mock_image_open, \
             patch('os.makedirs') as mock_makedirs:
            # Mock PIL.Image.open to return a dummy image
            dummy_image = MagicMock(spec=Image.Image)
            dummy_image.save.return_value = None
            mock_image_open.return_value = dummy_image

            response = pdf2images(
                input_file_path="sample.pdf",
                pages=[0],
                output_format="png",
                output_directory="images"
            )

            # Assertions
            mock_isfile.assert_called_once_with("sample.pdf")
            mock_pdfplumber_open.assert_called_once_with("sample.pdf")
            mock_makedirs.assert_called_once_with("images", exist_ok=True)
            mock_image_open.assert_called_once()
            dummy_image.save.assert_called_once_with("images/image_1_1.png", format="PNG")
            self.assertEqual(response["error_code"], "SUCCESS")
            self.assertIsNone(response["error"])
            self.assertEqual(response["output"]["message"], "Images extracted and saved to 'images' in PNG format.")

    @patch('pdfplumber.open')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2images_success_save_to_directory_jpeg(self, mock_isfile, mock_pdfplumber_open):
        # Mock pdfplumber to return a PDF with two pages containing one image each
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.images = [
            {'x0': 50, 'top': 50, 'x1': 150, 'bottom': 150}
        ]
        mock_page2 = MagicMock()
        mock_page2.images = [
            {'x0': 250, 'top': 250, 'x1': 350, 'bottom': 350}
        ]
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        with patch('builtins.open', unittest.mock.mock_open()) as mock_file, \
             patch('PIL.Image.open') as mock_image_open, \
             patch('os.makedirs') as mock_makedirs:
            # Mock PIL.Image.open to return a dummy image
            dummy_image = MagicMock(spec=Image.Image)
            dummy_image.save.return_value = None
            mock_image_open.return_value = dummy_image

            response = pdf2images(
                input_file_path="sample.pdf",
                pages=[0, 1],
                output_format="jpeg",
                output_directory="images_jpeg"
            )

            # Assertions
            mock_isfile.assert_called_once_with("sample.pdf")
            mock_pdfplumber_open.assert_called_once_with("sample.pdf")
            mock_makedirs.assert_called_once_with("images_jpeg", exist_ok=True)
            self.assertEqual(mock_image_open.call_count, 2)
            dummy_image.save.assert_any_call("images_jpeg/image_1_1.jpeg", format="JPEG")
            dummy_image.save.assert_any_call("images_jpeg/image_2_2.jpeg", format="JPEG")
            self.assertEqual(response["error_code"], "SUCCESS")
            self.assertIsNone(response["error"])
            self.assertEqual(response["output"]["message"], "Images extracted and saved to 'images_jpeg' in JPEG format.")

    @patch('pdfplumber.open')
    @patch('os.path.isfile', return_value=True)
    def test_pdf2images_file_not_found(self, mock_isfile, mock_pdfplumber_open):
        response = pdf2images(
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
    def test_pdf2images_image_extraction_error(self, mock_isfile, mock_pdfplumber_open):
        # Mock pdfplumber to return a PDF with one page containing one image
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.images = [
            {'x0': 100, 'top': 100, 'x1': 200, 'bottom': 200}
        ]
        mock_pdf.pages = [mock_page]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        # Mock PIL.Image.open to raise an exception
        with patch('PIL.Image.open', side_effect=Exception("Failed to open image")):
            response = pdf2images(
                input_file_path="sample.pdf",
                pages=[0],
                output_format="png",
                output_directory=None
            )

            # Assertions
            mock_isfile.assert_called_once_with("sample.pdf")
            mock_pdfplumber_open.assert_called_once_with("sample.pdf")
            self.assertEqual(response["error_code"], "IMAGE_EXTRACTION_ERROR")
            self.assertIsNone(response["output"])
            self.assertIn("IMAGE_EXTRACTION_ERROR: Failed to extract image on page 1: Failed to open image", response["error"])

    @patch('pdfplumber.open', side_effect=Exception("Unexpected exception"))
    @patch('os.path.isfile', return_value=True)
    def test_pdf2images_unexpected_error(self, mock_isfile, mock_pdfplumber_open):
        response = pdf2images(
            input_file_path="sample.pdf",
            pages=None,
            output_format="png",
            output_directory=None
        )

        # Assertions
        mock_isfile.assert_called_once_with("sample.pdf")
        mock_pdfplumber_open.assert_called_once_with("sample.pdf")
        self.assertEqual(response["error_code"], "UNEXPECTED_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("UNEXPECTED_ERROR: Unexpected exception", response["error"])

    def test_pdf2images_validation_error_invalid_format(self):
        response = pdf2images(
            input_file_path="sample.pdf",
            pages=None,
            output_format="bmp",  # Invalid format
            output_directory=None
        )

        # Assertions
        self.assertEqual(response["error_code"], "VALIDATION_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("Invalid output format 'bmp'", response["error"])


if __name__ == "__main__":
    unittest.main()