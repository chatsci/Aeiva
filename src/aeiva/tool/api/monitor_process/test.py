# toolkit/system_toolkit/monitor_process/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.system_toolkit.monitor_process.api import monitor_process
import psutil

class TestMonitorProcess(unittest.TestCase):
    @patch('psutil.Process')
    def test_monitor_process_by_pid_success(self, mock_process):
        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_proc.name.return_value = 'python.exe'
        mock_proc.status.return_value = 'running'
        mock_proc.cpu_percent.return_value = 12.5
        mock_proc.memory_percent.return_value = 30.2
        mock_process.return_value = mock_proc

        response = monitor_process("1234")
        mock_process.assert_called_with(1234)
        mock_proc.name.assert_called_once()
        mock_proc.status.assert_called_once()
        mock_proc.cpu_percent.assert_called_once_with(interval=1.0)
        mock_proc.memory_percent.assert_called_once()
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"]["process_info"], [{
            "pid": 1234,
            "name": "python.exe",
            "status": "running",
            "cpu_percent": 12.5,
            "memory_percent": 30.2
        }])
        self.assertIsNone(response["error"])

    @patch('psutil.Process', side_effect=psutil.NoSuchProcess(pid=1234))
    def test_monitor_process_by_pid_not_found(self, mock_process):
        response = monitor_process("1234")
        mock_process.assert_called_with(1234)
        self.assertEqual(response["error_code"], "PROCESS_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("No process found with PID 1234.", response["error"])

    @patch('psutil.process_iter')
    def test_monitor_process_by_name_success(self, mock_process_iter):
        mock_proc1 = MagicMock()
        mock_proc1.info = {
            'pid': 1234,
            'name': 'python.exe',
            'status': 'running',
            'cpu_percent': 15.0,
            'memory_percent': 25.0
        }
        mock_proc2 = MagicMock()
        mock_proc2.info = {
            'pid': 5678,
            'name': 'python.exe',
            'status': 'sleeping',
            'cpu_percent': 5.0,
            'memory_percent': 10.0
        }
        mock_process_iter.return_value = [mock_proc1, mock_proc2]

        response = monitor_process("python.exe")
        mock_process_iter.assert_called_once_with(['name'])
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"]["process_info"], [
            {
                "pid": 1234,
                "name": "python.exe",
                "status": "running",
                "cpu_percent": 15.0,
                "memory_percent": 25.0
            },
            {
                "pid": 5678,
                "name": "python.exe",
                "status": "sleeping",
                "cpu_percent": 5.0,
                "memory_percent": 10.0
            }
        ])
        self.assertIsNone(response["error"])

    @patch('psutil.process_iter', return_value=[])
    def test_monitor_process_by_name_not_found(self, mock_process_iter):
        response = monitor_process("nonexistent_app")
        mock_process_iter.assert_called_once_with(['name'])
        self.assertEqual(response["error_code"], "PROCESS_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("No process found with name 'nonexistent_app'.", response["error"])

    @patch('psutil.process_iter', side_effect=Exception("Mocked exception"))
    def test_monitor_process_unexpected_error(self, mock_process_iter):
        response = monitor_process("any_app")
        mock_process_iter.assert_called_once_with(['name'])
        self.assertEqual(response["error_code"], "FAILED_TO_MONITOR_PROCESS")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to monitor process 'any_app': Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()