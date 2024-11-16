# toolkit/file_toolkit/change_permissions/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.file_toolkit.change_permissions.api import change_permissions
import os
import platform
import subprocess

class TestChangePermissions(unittest.TestCase):
    @patch('os.chmod')
    @patch('os.path.exists', return_value=True)
    @patch('platform.system', return_value='Linux')
    def test_change_permissions_success_linux(self, mock_system, mock_exists, mock_chmod):
        response = change_permissions("/path/to/file", 0o755)
        mock_exists.assert_called_with("/path/to/file")
        mock_chmod.assert_called_with("/path/to/file", 0o755)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "Permissions for '/path/to/file' changed to '0o755' successfully.")
        self.assertIsNone(response["error"])

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    @patch('platform.system', return_value='Windows')
    def test_change_permissions_success_windows(self, mock_system, mock_exists, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Successfully processed 1 files.", stderr="")
        response = change_permissions("C:\\path\\to\\file", 0o755)
        mock_exists.assert_called_with("C:\\path\\to\\file")
        mock_run.assert_called_with(['icacls', 'C:\\path\\to\\file', '/grant', 'Everyone:(R,W)'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "Permissions for 'C:\\path\\to\\file' changed to '0o755' successfully.")
        self.assertIsNone(response["error"])

    @patch('os.path.exists', return_value=False)
    def test_change_permissions_path_not_found(self, mock_exists):
        response = change_permissions("/nonexistent/path", 0o755)
        mock_exists.assert_called_with("/nonexistent/path")
        self.assertEqual(response["error_code"], "PATH_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("Path '/nonexistent/path' does not exist.", response["error"])

    @patch('os.chmod', side_effect=PermissionError)
    @patch('os.path.exists', return_value=True)
    @patch('platform.system', return_value='Linux')
    def test_change_permissions_permission_denied_linux(self, mock_system, mock_exists, mock_chmod):
        response = change_permissions("/path/to/file", 0o755)
        mock_exists.assert_called_with("/path/to/file")
        mock_chmod.assert_called_with("/path/to/file", 0o755)
        self.assertEqual(response["error_code"], "PERMISSION_DENIED")
        self.assertIsNone(response["output"])
        self.assertIn("Permission denied while changing permissions for '/path/to/file'.", response["error"])

    @patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, ['icacls'], stderr="Error changing permissions."))
    @patch('os.path.exists', return_value=True)
    @patch('platform.system', return_value='Windows')
    def test_change_permissions_failed_windows(self, mock_system, mock_exists, mock_run):
        response = change_permissions("C:\\path\\to\\file", 0o755)
        mock_exists.assert_called_with("C:\\path\\to\\file")
        mock_run.assert_called_with(['icacls', 'C:\\path\\to\\file', '/grant', 'Everyone:(R,W)'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "FAILED_TO_CHANGE_PERMISSIONS")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to change permissions for 'C:\\path\\to\\file': Error changing permissions.", response["error"])

    @patch('os.chmod', side_effect=Exception("Mocked exception"))
    @patch('os.path.exists', return_value=True)
    @patch('platform.system', return_value='Linux')
    def test_change_permissions_unexpected_error_linux(self, mock_system, mock_exists, mock_chmod):
        response = change_permissions("/path/to/file", 0o755)
        mock_exists.assert_called_with("/path/to/file")
        mock_chmod.assert_called_with("/path/to/file", 0o755)
        self.assertEqual(response["error_code"], "FAILED_TO_CHANGE_PERMISSIONS")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to change permissions for '/path/to/file': Mocked exception", response["error"])

    @patch('platform.system', return_value='UnknownOS')
    @patch('os.path.exists', return_value=True)
    def test_change_permissions_unsupported_os(self, mock_exists, mock_system):
        response = change_permissions("/path/to/file", 0o755)
        mock_exists.assert_called_with("/path/to/file")
        self.assertEqual(response["error_code"], "UNSUPPORTED_OS")
        self.assertIsNone(response["output"])
        self.assertIn("Unsupported operating system: UnknownOS", response["error"])

if __name__ == "__main__":
    unittest.main()