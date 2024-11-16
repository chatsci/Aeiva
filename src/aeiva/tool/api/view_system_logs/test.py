# toolkit/system_toolkit/view_system_logs/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.system_toolkit.view_system_logs.api import view_system_logs

class TestViewSystemLogs(unittest.TestCase):
    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run')
    def test_view_system_logs_success_system_linux(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="System log entry 1\nSystem log entry 2", stderr="")
        response = view_system_logs("system")
        mock_run.assert_called_with(['journalctl', '-n', '100'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"]["logs"], "System log entry 1\nSystem log entry 2")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run')
    def test_view_system_logs_success_application_linux(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="Application log entry 1\nApplication log entry 2", stderr="")
        response = view_system_logs("application")
        mock_run.assert_called_with(['journalctl', '-u', 'application_name', '-n', '100'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"]["logs"], "Application log entry 1\nApplication log entry 2")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, ['journalctl'], stderr="Error retrieving logs."))
    def test_view_system_logs_failed_linux(self, mock_run, mock_system):
        response = view_system_logs("system")
        mock_run.assert_called_with(['journalctl', '-n', '100'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "FAILED_TO_VIEW_LOGS")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to retrieve logs: Error retrieving logs.", response["error"])

    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run')
    def test_view_system_logs_success_windows_system(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="System log entry 1\nSystem log entry 2", stderr="")
        response = view_system_logs("system")
        mock_run.assert_called_with(['wevtutil', 'qe', 'System', '/c:100', '/f:text'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"]["logs"], "System log entry 1\nSystem log entry 2")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run')
    def test_view_system_logs_success_windows_application(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="Application log entry 1\nApplication log entry 2", stderr="")
        response = view_system_logs("application")
        mock_run.assert_called_with(['wevtutil', 'qe', 'Application', '/c:100', '/f:text'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"]["logs"], "Application log entry 1\nApplication log entry 2")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, ['wevtutil'], stderr="Error retrieving logs."))
    def test_view_system_logs_failed_windows(self, mock_run, mock_system):
        response = view_system_logs("system")
        mock_run.assert_called_with(['wevtutil', 'qe', 'System', '/c:100', '/f:text'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "FAILED_TO_VIEW_LOGS")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to retrieve logs: Error retrieving logs.", response["error"])

    @patch('platform.system', return_value='Linux')
    def test_view_system_logs_unsupported_log_type(self, mock_system):
        response = view_system_logs("unsupported_type")
        self.assertEqual(response["error_code"], "UNSUPPORTED_LOG_TYPE")
        self.assertIsNone(response["output"])
        self.assertIn("Unsupported log type: unsupported_type", response["error"])

    @patch('platform.system', return_value='UnknownOS')
    def test_view_system_logs_unsupported_os(self, mock_system):
        response = view_system_logs("system")
        self.assertEqual(response["error_code"], "UNSUPPORTED_OS")
        self.assertIsNone(response["output"])
        self.assertIn("Unsupported operating system: UnknownOS", response["error"])

if __name__ == "__main__":
    unittest.main()