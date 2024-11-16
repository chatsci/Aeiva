# toolkit/system_toolkit/check_internet_connection/test.py

import unittest
from unittest.mock import patch
from toolkit.system_toolkit.check_internet_connection.api import check_internet_connection
import socket

class TestCheckInternetConnection(unittest.TestCase):
    @patch('socket.socket')
    def test_check_internet_connection_success(self, mock_socket):
        mock_sock_instance = MagicMock()
        mock_socket.return_value = mock_sock_instance
        response = check_internet_connection()
        mock_socket.assert_called_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_sock_instance.connect.assert_called_with(("8.8.8.8", 53))
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"]["is_connected"], True)
        self.assertIsNone(response["error"])

    @patch('socket.socket', side_effect=socket.error)
    def test_check_internet_connection_failure(self, mock_socket):
        response = check_internet_connection()
        mock_socket.assert_called_with(socket.AF_INET, socket.SOCK_STREAM)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"]["is_connected"], False)
        self.assertIsNone(response["error"])

    @patch('socket.socket', side_effect=Exception("Mocked exception"))
    def test_check_internet_connection_unexpected_error(self, mock_socket):
        response = check_internet_connection()
        mock_socket.assert_called_with(socket.AF_INET, socket.SOCK_STREAM)
        self.assertEqual(response["error_code"], "FAILED_TO_CHECK_CONNECTION")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to check internet connection: Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()