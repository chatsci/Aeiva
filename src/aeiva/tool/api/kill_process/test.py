# toolkit/system_toolkit/kill_process/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.system_toolkit.kill_process.api import kill_process
import psutil

class TestKillProcess(unittest.TestCase):
    @patch('psutil.Process')
    def test_kill_process_by_pid_success(self, mock_process):
        mock_proc = MagicMock()
        mock_process.return_value = mock_proc
        response = kill_process("1234")
        mock_process.assert_called_with(1234)
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once_with(timeout=5)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "Process with PID 1234 terminated successfully.")
        self.assertIsNone(response["error"])

    @patch('psutil.Process')
    def test_kill_process_by_pid_not_found(self, mock_process):
        mock_process.side_effect = psutil.NoSuchProcess(pid=1234)
        response = kill_process("1234")
        mock_process.assert_called_with(1234)
        self.assertEqual(response["error_code"], "PROCESS_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("No process found with PID 1234.", response["error"])

    @patch('psutil.Process')
    def test_kill_process_by_pid_timeout(self, mock_process):
        mock_proc = MagicMock()
        mock_proc.wait.side_effect = psutil.TimeoutExpired(pid=1234, timeout=5)
        mock_process.return_value = mock_proc
        response = kill_process("1234")
        mock_process.assert_called_with(1234)
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once_with(timeout=5)
        self.assertEqual(response["error_code"], "TERMINATION_TIMEOUT")
        self.assertIsNone(response["output"])
        self.assertIn("Process with PID 1234 did not terminate in time.", response["error"])

    @patch('psutil.Process')
    def test_kill_process_by_pid_failed_to_terminate(self, mock_process):
        mock_proc = MagicMock()
        mock_proc.terminate.side_effect = psutil.AccessDenied(pid=1234)
        mock_process.return_value = mock_proc
        response = kill_process("1234")
        mock_process.assert_called_with(1234)
        mock_proc.terminate.assert_called_once()
        self.assertEqual(response["error_code"], "FAILED_TO_TERMINATE")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to terminate process with PID 1234:", response["error"])

    @patch('psutil.process_iter')
    def test_kill_process_by_name_success(self, mock_process_iter):
        mock_proc = MagicMock()
        mock_proc.info = {'name': 'notepad.exe'}
        mock_process_iter.return_value = [mock_proc]
        response = kill_process("notepad.exe")
        mock_process_iter.assert_called_once_with(['name'])
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once_with(timeout=5)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "All instances of 'notepad.exe' terminated successfully.")
        self.assertIsNone(response["error"])

    @patch('psutil.process_iter')
    def test_kill_process_by_name_not_found(self, mock_process_iter):
        mock_process_iter.return_value = []
        response = kill_process("nonexistent_app")
        mock_process_iter.assert_called_once_with(['name'])
        self.assertEqual(response["error_code"], "PROCESS_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("No process found with name 'nonexistent_app'.", response["error"])

    @patch('psutil.process_iter')
    def test_kill_process_by_name_timeout(self, mock_process_iter):
        mock_proc = MagicMock()
        mock_proc.info = {'name': 'some_app'}
        mock_proc.terminate.return_value = None
        mock_proc.wait.side_effect = psutil.TimeoutExpired(pid=5678, timeout=5)
        mock_process_iter.return_value = [mock_proc]
        response = kill_process("some_app")
        mock_process_iter.assert_called_once_with(['name'])
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once_with(timeout=5)
        self.assertEqual(response["error_code"], "TERMINATION_TIMEOUT")
        self.assertIsNone(response["output"])
        self.assertIn("Process 'some_app' did not terminate in time.", response["error"])

    @patch('psutil.process_iter')
    def test_kill_process_by_name_failed_to_terminate(self, mock_process_iter):
        mock_proc = MagicMock()
        mock_proc.info = {'name': 'some_app'}
        mock_proc.terminate.side_effect = psutil.AccessDenied(pid=5678)
        mock_process_iter.return_value = [mock_proc]
        response = kill_process("some_app")
        mock_process_iter.assert_called_once_with(['name'])
        mock_proc.terminate.assert_called_once()
        self.assertEqual(response["error_code"], "FAILED_TO_TERMINATE")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to terminate process 'some_app':", response["error"])

    @patch('psutil.process_iter', side_effect=Exception("Mocked exception"))
    def test_kill_process_unexpected_error(self, mock_process_iter):
        response = kill_process("any_app")
        mock_process_iter.assert_called_once_with(['name'])
        self.assertEqual(response["error_code"], "UNEXPECTED_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("An unexpected error occurred: Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()