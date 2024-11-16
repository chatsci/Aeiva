# toolkit/system_toolkit/delete_user/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.system_toolkit.delete_user.api import delete_user

class TestDeleteUser(unittest.TestCase):
    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run')
    def test_delete_user_success_linux(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="userdel executed successfully.", stderr="")
        response = delete_user("testuser")
        mock_run.assert_called_with(['sudo', 'userdel', '-r', 'testuser'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "User 'testuser' deleted successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Darwin')
    @patch('subprocess.run')
    def test_delete_user_success_mac(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="userdel executed successfully.", stderr="")
        response = delete_user("testuser")
        mock_run.assert_called_with(['sudo', 'userdel', '-r', 'testuser'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "User 'testuser' deleted successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run')
    def test_delete_user_success_windows(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="The command completed successfully.", stderr="")
        response = delete_user("testuser")
        mock_run.assert_called_with(['net', 'user', 'testuser', '/delete'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "User 'testuser' deleted successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, ['userdel'], stderr="Error deleting user."))
    def test_delete_user_failed_linux(self, mock_run, mock_system):
        response = delete_user("testuser")
        mock_run.assert_called_with(['sudo', 'userdel', '-r', 'testuser'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "FAILED_TO_DELETE_USER")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to delete user 'testuser': Error deleting user.", response["error"])

    @patch('platform.system', return_value='UnknownOS')
    def test_delete_user_unsupported_os(self, mock_system):
        response = delete_user("testuser")
        self.assertEqual(response["error_code"], "UNSUPPORTED_OS")
        self.assertIsNone(response["output"])
        self.assertIn("Unsupported operating system: UnknownOS", response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run', side_effect=Exception("Mocked exception"))
    def test_delete_user_unexpected_error(self, mock_run, mock_system):
        response = delete_user("testuser")
        mock_run.assert_called_with(['sudo', 'userdel', '-r', 'testuser'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "FAILED_TO_DELETE_USER")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to delete user 'testuser': Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()