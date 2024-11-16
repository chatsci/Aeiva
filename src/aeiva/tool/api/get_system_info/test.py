# toolkit/system_toolkit/get_system_info/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.system_toolkit.get_system_info.api import get_system_info
import platform

class TestGetSystemInfo(unittest.TestCase):
    def test_get_system_info_success(self):
        response = get_system_info()
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNotNone(response["output"]["system_info"])
        self.assertIsInstance(response["output"]["system_info"], dict)
        self.assertIn("system", response["output"]["system_info"])
        self.assertIn("cpu_count_logical", response["output"]["system_info"])
        self.assertIn("memory_percent", response["output"]["system_info"])

    @patch('platform.uname', side_effect=Exception("Mocked exception"))
    def test_get_system_info_unexpected_error(self, mock_uname):
        response = get_system_info()
        self.assertEqual(response["error_code"], "UNEXPECTED_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("An unexpected error occurred: Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()