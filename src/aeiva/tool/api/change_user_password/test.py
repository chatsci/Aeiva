# toolkit/system_toolkit/change_user_password/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.system_toolkit.change_user_password.api import change_user_password

class TestChangeUserPassword(unittest.TestCase):
    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run')
    def test_change_user_password_success_linux(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        response = change_user_password("testuser", "newpass")
        mock_run.assert_called_with(['sudo', 'chpasswd'], input='testuser:newpass', check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "Password for user 'testuser' updated successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Darwin')
    @patch('subprocess.run')
    def test_change_user_password_success_mac(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        response = change_user_password("testuser", "newpass")
        mock_run.assert_called_with(['sudo', 'chpasswd'], input='testuser:newpass', check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "Password for user 'testuser' updated successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run')
    def test_change_user_password_success_windows(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="The command completed successfully.", stderr="")
        response = change_user_password("testuser", "newpass")
        mock_run.assert_called_with(['net', 'user', 'testuser', 'newpass'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "Password for user 'testuser' updated successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, ['chpasswd'], stderr="Error changing password."))
    def test_change_user_password_failed_linux(self, mock_run, mock_system):
        response = change_user_password("testuser", "newpass")
        mock_run.assert_called_with(['sudo', 'chpasswd'], input='testuser:newpass', check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "FAILED_TO_CHANGE_PASSWORD")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to change password for user 'testuser': Error changing password.", response["error"])

    @patch('platform.system', return_value='UnknownOS')
    def test_change_user_password_unsupported_os(self, mock_system):
        response = change_user_password("testuser", "newpass")
        self.assertEqual(response["error_code"], "UNSUPPORTED_OS")
        self.assertIsNone(response["output"])
        self.assertIn("Unsupported operating system: UnknownOS", response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run', side_effect=Exception("Mocked exception"))
    def test_change_user_password_unexpected_error(self, mock_run, mock_system):
        response = change_user_password("testuser", "newpass")
        mock_run.assert_called_with(['sudo', 'chpasswd'], input='testuser:newpass', check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "FAILED_TO_CHANGE_PASSWORD")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to change password for user 'testuser': Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()