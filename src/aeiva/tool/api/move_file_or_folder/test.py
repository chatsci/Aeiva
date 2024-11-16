# toolkit/file_toolkit/move_file_or_folder/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.file_toolkit.move_file_or_folder.api import move_file_or_folder

class TestMoveFileOrFolder(unittest.TestCase):
    @patch('shutil.move')
    @patch('os.path.exists', return_value=True)
    def test_move_file_success(self, mock_exists, mock_move):
        response = move_file_or_folder("source.txt", "destination.txt")
        mock_exists.assert_called_with("source.txt")
        mock_move.assert_called_with("source.txt", "destination.txt")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "Moved 'source.txt' to 'destination.txt' successfully.")
        self.assertIsNone(response["error"])

    @patch('shutil.move', side_effect=FileNotFoundError)
    @patch('os.path.exists', return_value=False)
    def test_move_source_not_found(self, mock_exists, mock_move):
        response = move_file_or_folder("nonexistent.txt", "destination.txt")
        mock_exists.assert_called_with("nonexistent.txt")
        mock_move.assert_not_called()
        self.assertEqual(response["error_code"], "SOURCE_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("Source path 'nonexistent.txt' does not exist.", response["error"])

    @patch('shutil.move', side_effect=PermissionError)
    @patch('os.path.exists', return_value=True)
    def test_move_permission_denied(self, mock_exists, mock_move):
        response = move_file_or_folder("source.txt", "destination.txt")
        mock_exists.assert_called_with("source.txt")
        mock_move.assert_called_with("source.txt", "destination.txt")
        self.assertEqual(response["error_code"], "PERMISSION_DENIED")
        self.assertIsNone(response["output"])
        self.assertIn("Permission denied while moving 'source.txt' to 'destination.txt'.", response["error"])

    @patch('shutil.move', side_effect=shutil.Error("Error moving file."))
    @patch('os.path.exists', return_value=True)
    def test_move_shutil_error(self, mock_exists, mock_move):
        response = move_file_or_folder("source.txt", "destination.txt")
        mock_exists.assert_called_with("source.txt")
        mock_move.assert_called_with("source.txt", "destination.txt")
        self.assertEqual(response["error_code"], "SHUTIL_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("Error moving 'source.txt' to 'destination.txt': Error moving file.", response["error"])

    @patch('shutil.move', side_effect=Exception("Mocked exception"))
    @patch('os.path.exists', return_value=True)
    def test_move_unexpected_error(self, mock_exists, mock_move):
        response = move_file_or_folder("source.txt", "destination.txt")
        mock_exists.assert_called_with("source.txt")
        mock_move.assert_called_with("source.txt", "destination.txt")
        self.assertEqual(response["error_code"], "FAILED_TO_MOVE")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to move 'source.txt' to 'destination.txt': Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()