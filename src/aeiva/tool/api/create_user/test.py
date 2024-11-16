# toolkit/system_toolkit/create_user/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.system_toolkit.create_user.api import create_user

class TestCreateUser(unittest.TestCase):
    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run')
    def test_create_user_success_linux(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="User added successfully.", stderr="")
        response = create_user("testuser", "testpass")
        mock_run.assert_any_call(['sudo', 'useradd', '-m', '-s', '/bin/bash', 'testuser'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        mock_run.assert_any_call(['sudo', 'chpasswd'], input='testuser:testpass', check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "User 'testuser' created successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Darwin')
    @patch('subprocess.run')
    def test_create_user_success_mac(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="User added successfully.", stderr="")
        response = create_user("testuser", "testpass")
        mock_run.assert_any_call(['sudo', 'useradd', '-m', '-s', '/bin/bash', 'testuser'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        mock_run.assert_any_call(['sudo', 'chpasswd'], input='testuser:testpass', check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "User 'testuser' created successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run')
    def test_create_user_success_windows(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="The command completed successfully.", stderr="")
        response = create_user("testuser", "testpass")
        mock_run.assert_called_with(['net', 'user', 'testuser', 'testpass', '/add'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "User 'testuser' created successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, ['useradd'], stderr="Error adding user."))
    def test_create_user_failed_linux(self, mock_run, mock_system):
        response = create_user("testuser", "testpass")
        mock_run.assert_any_call(['sudo', 'useradd', '-m', '-s', '/bin/bash', 'testuser'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "FAILED_TO_CREATE_USER")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to create user 'testuser': Error adding user.", response["error"])

    @patch('platform.system', return_value='UnknownOS')
    def test_create_user_unsupported_os(self, mock_system):
        response = create_user("testuser", "testpass")
        self.assertEqual(response["error_code"], "UNSUPPORTED_OS")
        self.assertIsNone(response["output"])
        self.assertIn("Unsupported operating system: UnknownOS", response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run', side_effect=Exception("Mocked exception"))
    def test_create_user_unexpected_error(self, mock_run, mock_system):
        response = create_user("testuser", "testpass")
        mock_run.assert_called_with(['sudo', 'useradd', '-m', '-s', '/bin/bash', 'testuser'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "FAILED_TO_CREATE_USER")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to create user 'testuser': Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()