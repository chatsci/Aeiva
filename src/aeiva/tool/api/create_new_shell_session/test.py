# toolkit/shell_toolkit/create_new_shell_session/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.shell_toolkit.create_new_shell_session.api import create_new_shell_session

class TestCreateNewShellSession(unittest.TestCase):
    @patch('subprocess.Popen')
    @patch('platform.system', return_value='Linux')
    def test_create_new_shell_session_success_default_shell_linux(self, mock_system, mock_popen):
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        response = create_new_shell_session()
        
        mock_system.assert_called_once()
        mock_popen.assert_called_once_with(['/bin/bash'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        self.assertIn("session_id", response["output"])
        self.assertIn("session_name", response["output"])
    
    @patch('subprocess.Popen')
    @patch('platform.system', return_value='Darwin')
    def test_create_new_shell_session_success_custom_shell_mac(self, mock_system, mock_popen):
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        response = create_new_shell_session(session_name="my_session", shell_type="/bin/zsh")
        
        mock_system.assert_called_once()
        mock_popen.assert_called_once_with(['/bin/zsh'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        self.assertIn("session_id", response["output"])
        self.assertEqual(response["output"]["session_name"], "my_session")
    
    @patch('subprocess.Popen', side_effect=FileNotFoundError)
    @patch('platform.system', return_value='Linux')
    def test_create_new_shell_session_shell_not_found_linux(self, mock_system, mock_popen):
        response = create_new_shell_session(shell_type="/bin/nonexistent_shell")
        
        mock_system.assert_called_once()
        mock_popen.assert_called_once_with(['/bin/nonexistent_shell'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SHELL_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("Shell '/bin/nonexistent_shell' not found on the system.", response["error"])
    
    @patch('subprocess.Popen', side_effect=PermissionError)
    @patch('platform.system', return_value='Linux')
    def test_create_new_shell_session_permission_denied_linux(self, mock_system, mock_popen):
        response = create_new_shell_session(shell_type="/bin/bash")
        
        mock_system.assert_called_once()
        mock_popen.assert_called_once_with(['/bin/bash'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "PERMISSION_DENIED")
        self.assertIsNone(response["output"])
        self.assertIn("Permission denied while trying to start shell '/bin/bash'.", response["error"])
    
    @patch('subprocess.Popen', side_effect=Exception("Mocked exception"))
    @patch('platform.system', return_value='Linux')
    def test_create_new_shell_session_unexpected_error_linux(self, mock_system, mock_popen):
        response = create_new_shell_session(shell_type="/bin/bash")
        
        mock_system.assert_called_once()
        mock_popen.assert_called_once_with(['/bin/bash'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "FAILED_TO_CREATE_SESSION")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to create new shell session: Mocked exception", response["error"])
    
    @patch('platform.system', return_value='Windows')
    @patch('subprocess.Popen')
    def test_create_new_shell_session_success_powershell_windows(self, mock_popen, mock_system):
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        response = create_new_shell_session(session_name="win_session", shell_type="powershell")
        
        mock_system.assert_called_once()
        mock_popen.assert_called_once_with(['powershell', '-NoExit'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        self.assertIn("session_id", response["output"])
        self.assertEqual(response["output"]["session_name"], "win_session")
    
    @patch('platform.system', return_value='Windows')
    @patch('subprocess.Popen', side_effect=FileNotFoundError)
    def test_create_new_shell_session_shell_not_found_windows(self, mock_popen, mock_system):
        response = create_new_shell_session(shell_type="invalid_shell")
        
        mock_system.assert_called_once()
        mock_popen.assert_called_once_with(['invalid_shell'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SHELL_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("Shell 'invalid_shell' not found on the system.", response["error"])
    
    @patch('platform.system', return_value='UnknownOS')
    def test_create_new_shell_session_unsupported_os(self, mock_system):
        response = create_new_shell_session()
        
        mock_system.assert_called_once()
        self.assertEqual(response["error_code"], "UNSUPPORTED_OS")
        self.assertIsNone(response["output"])
        self.assertIn("Unsupported operating system: UnknownOS", response["error"])
    
    @patch('platform.system', return_value='Linux')
    @patch('subprocess.Popen', side_effect=Exception("Mocked exception"))
    def test_create_new_shell_session_unexpected_error_linux(self, mock_popen, mock_system):
        response = create_new_shell_session()
        
        mock_system.assert_called_once()
        mock_popen.assert_called_once_with(['/bin/bash'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "FAILED_TO_CREATE_SESSION")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to create new shell session: Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()