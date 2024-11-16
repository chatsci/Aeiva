# toolkit/file_toolkit/get_file_metadata/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.file_toolkit.get_file_metadata.api import get_file_metadata
import os
import subprocess

class TestGetFileMetadata(unittest.TestCase):
    @patch('os.path.exists', return_value=True)
    @patch('platform.system', return_value='Linux')
    @patch('os.stat')
    def test_get_file_metadata_success_linux(self, mock_stat, mock_system, mock_exists):
        mock_stat.return_value = os.stat_result((0o755, 0, 0, 0, 0, 0, 123456789, 987654321, 123456789, 987654321))
        response = get_file_metadata("/path/to/file")
        mock_exists.assert_called_with("/path/to/file")
        mock_stat.assert_called_with("/path/to/file")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        self.assertEqual(response["output"]["metadata"], {
            "mode": "0o755",
            "size": 123456789,
            "last_modified": 987654321,
            "last_accessed": 123456789,
            "created": 987654321
        })

    @patch('os.path.exists', return_value=True)
    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run')
    def test_get_file_metadata_success_windows(self, mock_run, mock_system, mock_exists):
        mock_run.return_value = MagicMock(returncode=0, stdout='{"Mode": "RW-", "Length": 1024, "LastWriteTime": "2023-10-01T12:34:56", "LastAccessTime": "2023-10-01T12:34:56", "CreationTime": "2023-10-01T12:34:56"}', stderr="")
        response = get_file_metadata("C:\\path\\to\\file")
        mock_exists.assert_called_with("C:\\path\\to\\file")
        mock_run.assert_called_with(['powershell', '-Command', "Get-Item 'C:\\path\\to\\file' | Select-Object Mode, Length, LastWriteTime, LastAccessTime, CreationTime | ConvertTo-Json"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        self.assertEqual(response["output"]["metadata"], '{"Mode": "RW-", "Length": 1024, "LastWriteTime": "2023-10-01T12:34:56", "LastAccessTime": "2023-10-01T12:34:56", "CreationTime": "2023-10-01T12:34:56"}')

    @patch('os.path.exists', return_value=False)
    def test_get_file_metadata_path_not_found(self, mock_exists):
        response = get_file_metadata("/nonexistent/path")
        mock_exists.assert_called_with("/nonexistent/path")
        self.assertEqual(response["error_code"], "PATH_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("Path '/nonexistent/path' does not exist.", response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('os.path.exists', return_value=True)
    @patch('os.stat', side_effect=PermissionError)
    def test_get_file_metadata_permission_denied_linux(self, mock_stat, mock_exists, mock_system):
        response = get_file_metadata("/path/to/protected_file")
        mock_exists.assert_called_with("/path/to/protected_file")
        mock_stat.assert_called_with("/path/to/protected_file")
        self.assertEqual(response["error_code"], "FAILED_TO_GET_METADATA")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to retrieve metadata for '/path/to/protected_file': ", response["error"])

    @patch('platform.system', return_value='Windows')
    @patch('os.path.exists', return_value=True)
    @patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, ['powershell'], stderr="Error retrieving metadata."))
    def test_get_file_metadata_failed_windows(self, mock_run, mock_system, mock_exists):
        response = get_file_metadata("C:\\path\\to\\file")
        mock_exists.assert_called_with("C:\\path\\to\\file")
        mock_run.assert_called_with(['powershell', '-Command', "Get-Item 'C:\\path\\to\\file' | Select-Object Mode, Length, LastWriteTime, LastAccessTime, CreationTime | ConvertTo-Json"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "FAILED_TO_GET_METADATA")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to retrieve metadata for 'C:\\path\\to\\file': Error retrieving metadata.", response["error"])

    @patch('platform.system', return_value='UnknownOS')
    @patch('os.path.exists', return_value=True)
    def test_get_file_metadata_unsupported_os(self, mock_exists, mock_system):
        response = get_file_metadata("/path/to/file")
        mock_exists.assert_called_with("/path/to/file")
        self.assertEqual(response["error_code"], "UNSUPPORTED_OS")
        self.assertIsNone(response["output"])
        self.assertIn("Unsupported operating system: UnknownOS", response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('os.path.exists', return_value=True)
    @patch('os.stat', side_effect=Exception("Mocked exception"))
    def test_get_file_metadata_unexpected_error_linux(self, mock_stat, mock_exists, mock_system):
        response = get_file_metadata("/path/to/file")
        mock_exists.assert_called_with("/path/to/file")
        mock_stat.assert_called_with("/path/to/file")
        self.assertEqual(response["error_code"], "FAILED_TO_GET_METADATA")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to retrieve metadata for '/path/to/file': Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()