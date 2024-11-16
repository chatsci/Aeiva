# toolkit/file_toolkit/copy_file_or_folder/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.file_toolkit.copy_file_or_folder.api import copy_file_or_folder

class TestCopyFileOrFolder(unittest.TestCase):
    @patch('shutil.copy2')
    @patch('os.path.isdir', return_value=False)
    @patch('os.path.exists', return_value=True)
    def test_copy_file_success(self, mock_exists, mock_isdir, mock_copy2):
        response = copy_file_or_folder("source.txt", "destination.txt")
        mock_exists.assert_called_with("source.txt")
        mock_isdir.assert_called_with("source.txt")
        mock_copy2.assert_called_with("source.txt", "destination.txt")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "Copied 'source.txt' to 'destination.txt' successfully.")
        self.assertIsNone(response["error"])

    @patch('shutil.copytree')
    @patch('os.path.isdir', return_value=True)
    @patch('os.path.exists', return_value=True)
    def test_copy_folder_success(self, mock_exists, mock_isdir, mock_copytree):
        response = copy_file_or_folder("source_folder", "destination_folder")
        mock_exists.assert_called_with("source_folder")
        mock_isdir.assert_called_with("source_folder")
        mock_copytree.assert_called_with("source_folder", "destination_folder")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "Copied 'source_folder' to 'destination_folder' successfully.")
        self.assertIsNone(response["error"])

    @patch('os.path.exists', return_value=False)
    def test_copy_source_not_found(self, mock_exists):
        response = copy_file_or_folder("nonexistent.txt", "destination.txt")
        mock_exists.assert_called_with("nonexistent.txt")
        self.assertEqual(response["error_code"], "SOURCE_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("Source path 'nonexistent.txt' does not exist.", response["error"])

    @patch('shutil.copy2', side_effect=FileExistsError)
    @patch('os.path.isdir', return_value=False)
    @patch('os.path.exists', return_value=True)
    def test_copy_destination_exists_file(self, mock_exists, mock_isdir, mock_copy2):
        response = copy_file_or_folder("source.txt", "destination.txt")
        mock_exists.assert_called_with("source.txt")
        mock_isdir.assert_called_with("source.txt")
        mock_copy2.assert_called_with("source.txt", "destination.txt")
        self.assertEqual(response["error_code"], "DESTINATION_EXISTS")
        self.assertIsNone(response["output"])
        self.assertIn("Destination 'destination.txt' already exists.", response["error"])

    @patch('shutil.copytree', side_effect=FileExistsError)
    @patch('os.path.isdir', return_value=True)
    @patch('os.path.exists', return_value=True)
    def test_copy_destination_exists_folder(self, mock_exists, mock_isdir, mock_copytree):
        response = copy_file_or_folder("source_folder", "destination_folder")
        mock_exists.assert_called_with("source_folder")
        mock_isdir.assert_called_with("source_folder")
        mock_copytree.assert_called_with("source_folder", "destination_folder")
        self.assertEqual(response["error_code"], "DESTINATION_EXISTS")
        self.assertIsNone(response["output"])
        self.assertIn("Destination 'destination_folder' already exists.", response["error"])

    @patch('shutil.copy2', side_effect=PermissionError)
    @patch('os.path.isdir', return_value=False)
    @patch('os.path.exists', return_value=True)
    def test_copy_permission_denied_file(self, mock_exists, mock_isdir, mock_copy2):
        response = copy_file_or_folder("source.txt", "destination.txt")
        mock_exists.assert_called_with("source.txt")
        mock_isdir.assert_called_with("source.txt")
        mock_copy2.assert_called_with("source.txt", "destination.txt")
        self.assertEqual(response["error_code"], "PERMISSION_DENIED")
        self.assertIsNone(response["output"])
        self.assertIn("Permission denied while copying 'source.txt' to 'destination.txt'.", response["error"])

    @patch('shutil.copy2', side_effect=Exception("Mocked exception"))
    @patch('os.path.isdir', return_value=False)
    @patch('os.path.exists', return_value=True)
    def test_copy_unexpected_error_file(self, mock_exists, mock_isdir, mock_copy2):
        response = copy_file_or_folder("source.txt", "destination.txt")
        mock_exists.assert_called_with("source.txt")
        mock_isdir.assert_called_with("source.txt")
        mock_copy2.assert_called_with("source.txt", "destination.txt")
        self.assertEqual(response["error_code"], "FAILED_TO_COPY")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to copy 'source.txt' to 'destination.txt': Mocked exception", response["error"])

    @patch('shutil.copytree', side_effect=Exception("Mocked exception"))
    @patch('os.path.isdir', return_value=True)
    @patch('os.path.exists', return_value=True)
    def test_copy_unexpected_error_folder(self, mock_exists, mock_isdir, mock_copytree):
        response = copy_file_or_folder("source_folder", "destination_folder")
        mock_exists.assert_called_with("source_folder")
        mock_isdir.assert_called_with("source_folder")
        mock_copytree.assert_called_with("source_folder", "destination_folder")
        self.assertEqual(response["error_code"], "FAILED_TO_COPY")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to copy 'source_folder' to 'destination_folder': Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()