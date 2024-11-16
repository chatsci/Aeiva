# toolkit/system_toolkit/clean_temp_files/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.system_toolkit.clean_temp_files.api import clean_temp_files
import os
import shutil

class TestCleanTempFiles(unittest.TestCase):
    @patch('os.path.exists', return_value=True)
    @patch('os.path.isdir', return_value=True)
    @patch('os.listdir', return_value=['tempfile1.tmp', 'tempfile2.tmp'])
    @patch('os.unlink')
    @patch('shutil.rmtree')
    def test_clean_temp_files_success(self, mock_rmtree, mock_unlink, mock_listdir, mock_isdir, mock_exists):
        response = clean_temp_files(['C:/Temp'])
        mock_exists.assert_called_with('C:/Temp')
        mock_isdir.assert_called_with('C:/Temp')
        mock_listdir.assert_called_with('C:/Temp')
        mock_unlink.assert_any_call('C:/Temp/tempfile1.tmp')
        mock_unlink.assert_any_call('C:/Temp/tempfile2.tmp')
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        self.assertEqual(response["output"]["cleaned_files"], [
            'C:/Temp/tempfile1.tmp',
            'C:/Temp/tempfile2.tmp'
        ])
        self.assertEqual(response["output"]["failed_files"], {})

    @patch('os.path.exists', return_value=False)
    @patch('os.path.isdir', return_value=False)
    def test_clean_temp_files_path_not_exists(self, mock_isdir, mock_exists):
        response = clean_temp_files(['C:/NonExistent'])
        mock_exists.assert_called_with('C:/NonExistent')
        mock_isdir.assert_not_called()
        self.assertEqual(response["error_code"], "PARTIAL_SUCCESS")
        self.assertIn("Path does not exist.", response["output"]["failed_files"]["C:/NonExistent"])
        self.assertIsNotNone(response["error"])
        self.assertEqual(response["error"], "Some files/directories could not be deleted.")

    @patch('os.path.exists', return_value=True)
    @patch('os.path.isdir', return_value=False)
    def test_clean_temp_files_path_not_directory(self, mock_isdir, mock_exists):
        response = clean_temp_files(['C:/file.txt'])
        mock_exists.assert_called_with('C:/file.txt')
        mock_isdir.assert_called_with('C:/file.txt')
        self.assertEqual(response["error_code"], "PARTIAL_SUCCESS")
        self.assertIn("Path is not a directory.", response["output"]["failed_files"]["C:/file.txt"])
        self.assertIsNotNone(response["error"])
        self.assertEqual(response["error"], "Some files/directories could not be deleted.")

    @patch('os.path.exists', return_value=True)
    @patch('os.path.isdir', return_value=True)
    @patch('os.listdir', return_value=['tempfile1.tmp'])
    @patch('os.unlink', side_effect=Exception("Mocked delete error"))
    def test_clean_temp_files_failed_to_delete_file(self, mock_unlink, mock_listdir, mock_isdir, mock_exists):
        response = clean_temp_files(['C:/Temp'])
        mock_exists.assert_called_with('C:/Temp')
        mock_isdir.assert_called_with('C:/Temp')
        mock_listdir.assert_called_with('C:/Temp')
        mock_unlink.assert_called_with('C:/Temp/tempfile1.tmp')
        self.assertEqual(response["error_code"], "PARTIAL_SUCCESS")
        self.assertIn("Mocked delete error", response["output"]["failed_files"]["C:/Temp/tempfile1.tmp"])
        self.assertIsNotNone(response["error"])
        self.assertEqual(response["error"], "Some files/directories could not be deleted.")

    @patch('os.path.exists', return_value=True)
    @patch('os.path.isdir', return_value=True)
    @patch('os.listdir', side_effect=Exception("Mocked listdir error"))
    def test_clean_temp_files_unexpected_error(self, mock_listdir, mock_isdir, mock_exists):
        response = clean_temp_files(['C:/Temp'])
        mock_exists.assert_called_with('C:/Temp')
        mock_isdir.assert_called_with('C:/Temp')
        mock_listdir.assert_called_with('C:/Temp')
        self.assertEqual(response["error_code"], "FAILED_TO_CLEAN_TEMP_FILES")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to clean temporary files: Mocked listdir error", response["error"])

if __name__ == "__main__":
    unittest.main()