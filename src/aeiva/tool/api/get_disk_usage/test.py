# toolkit/system_toolkit/get_disk_usage/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.system_toolkit.get_disk_usage.api import get_disk_usage
import psutil

class TestGetDiskUsage(unittest.TestCase):
    @patch('psutil.disk_usage')
    def test_get_disk_usage_success(self, mock_disk_usage):
        mock_usage = MagicMock()
        mock_usage.total = 1000000
        mock_usage.used = 500000
        mock_usage.free = 500000
        mock_usage.percent = 50.0
        mock_disk_usage.return_value = mock_usage

        response = get_disk_usage("/")
        mock_disk_usage.assert_called_with("/")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"]["disk_usage"], {
            "total": 1000000,
            "used": 500000,
            "free": 500000,
            "percent": 50.0
        })
        self.assertIsNone(response["error"])

    @patch('psutil.disk_usage', side_effect=FileNotFoundError)
    def test_get_disk_usage_path_not_found(self, mock_disk_usage):
        response = get_disk_usage("/nonexistent/path")
        mock_disk_usage.assert_called_with("/nonexistent/path")
        self.assertEqual(response["error_code"], "PATH_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("The path '/nonexistent/path' does not exist.", response["error"])

    @patch('psutil.disk_usage', side_effect=Exception("Mocked exception"))
    def test_get_disk_usage_failed(self, mock_disk_usage):
        response = get_disk_usage("/")
        mock_disk_usage.assert_called_with("/")
        self.assertEqual(response["error_code"], "FAILED_TO_GET_DISK_USAGE")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to get disk usage for path '/': Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()