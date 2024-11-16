# toolkit/system_toolkit/get_network_info/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.system_toolkit.get_network_info.api import get_network_info
import psutil

class TestGetNetworkInfo(unittest.TestCase):
    @patch('psutil.net_if_addrs')
    @patch('psutil.net_if_stats')
    def test_get_network_info_success(self, mock_net_if_stats, mock_net_if_addrs):
        mock_net_if_addrs.return_value = {
            'eth0': [
                MagicMock(address='192.168.1.10'),
                MagicMock(address='fe80::1c35:42ff:fe1e:8329'),
            ],
            'lo': [
                MagicMock(address='127.0.0.1'),
                MagicMock(address='::1'),
            ]
        }
        mock_net_if_stats.return_value = {
            'eth0': MagicMock(isup=True, duplex=psutil.NIC_DUPLEX_FULL, speed=1000, mtu=1500),
            'lo': MagicMock(isup=True, duplex=None, speed=0, mtu=65536),
        }

        response = get_network_info()
        mock_net_if_addrs.assert_called_once()
        mock_net_if_stats.assert_called_once()
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNotNone(response["output"]["network_info"])
        self.assertIn('eth0', response["output"]["network_info"])
        self.assertIn('lo', response["output"]["network_info"])
        self.assertEqual(response["output"]["network_info"]['eth0']['addresses'], ['192.168.1.10', 'fe80::1c35:42ff:fe1e:8329'])
        self.assertTrue(response["output"]["network_info"]['eth0']['is_up'])
        self.assertEqual(response["output"]["network_info"]['eth0']['duplex'], 'FULL')
        self.assertEqual(response["output"]["network_info"]['eth0']['speed'], 1000)
        self.assertEqual(response["output"]["network_info"]['eth0']['mtu'], 1500)
        self.assertEqual(response["output"]["network_info"]['lo']['addresses'], ['127.0.0.1', '::1'])
        self.assertTrue(response["output"]["network_info"]['lo']['is_up'])
        self.assertEqual(response["output"]["network_info"]['lo']['duplex'], 'UNKNOWN')
        self.assertEqual(response["output"]["network_info"]['lo']['speed'], 0)
        self.assertEqual(response["output"]["network_info"]['lo']['mtu'], 65536)

    @patch('psutil.net_if_addrs', side_effect=Exception("Mocked exception"))
    @patch('psutil.net_if_stats')
    def test_get_network_info_unexpected_error(self, mock_net_if_stats, mock_net_if_addrs):
        response = get_network_info()
        mock_net_if_addrs.assert_called_once()
        self.assertEqual(response["error_code"], "UNEXPECTED_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("An unexpected error occurred: Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()