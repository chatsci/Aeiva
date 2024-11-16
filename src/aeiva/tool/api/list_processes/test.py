# toolkit/system_toolkit/list_processes/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.system_toolkit.list_processes.api import list_processes

class TestListProcesses(unittest.TestCase):
    @patch('psutil.process_iter')
    def test_list_processes_success(self, mock_process_iter):
        mock_proc1 = MagicMock()
        mock_proc1.info = {'pid': 1234, 'name': 'python.exe', 'username': 'testuser'}
        mock_proc2 = MagicMock()
        mock_proc2.info = {'pid': 5678, 'name': 'notepad.exe', 'username': 'testuser'}
        mock_process_iter.return_value = [mock_proc1, mock_proc2]

        response = list_processes()
        mock_process_iter.assert_called_once_with(['pid', 'name', 'username'])
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNotNone(response["output"]["processes"])
        self.assertEqual(len(response["output"]["processes"]), 2)
        self.assertEqual(response["output"]["processes"][0]['pid'], 1234)
        self.assertEqual(response["output"]["processes"][0]['name'], 'python.exe')
        self.assertEqual(response["output"]["processes"][0]['username'], 'testuser')

    @patch('psutil.process_iter', side_effect=Exception("Mocked exception"))
    def test_list_processes_unexpected_error(self, mock_process_iter):
        response = list_processes()
        mock_process_iter.assert_called_once_with(['pid', 'name', 'username'])
        self.assertEqual(response["error_code"], "UNEXPECTED_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("An unexpected error occurred: Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()