# toolkit/system_toolkit/monitor_system_resources/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.system_toolkit.monitor_system_resources.api import monitor_system_resources
import psutil

class TestMonitorSystemResources(unittest.TestCase):
    @patch('psutil.cpu_percent', return_value=15.0)
    @patch('psutil.virtual_memory')
    @patch('psutil.swap_memory')
    @patch('psutil.disk_partitions')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    def test_monitor_system_resources_success(self, mock_net_io, mock_disk_usage, mock_disk_partitions, mock_swap_memory, mock_virtual_memory, mock_cpu_percent):
        mock_virtual_memory.return_value = MagicMock(
            total=16000000000,
            available=8000000000,
            percent=50.0,
            used=8000000000,
            free=8000000000
        )
        mock_swap_memory.return_value = MagicMock(
            total=8000000000,
            used=2000000000,
            free=6000000000,
            percent=25.0
        )
        mock_disk_partitions.return_value = [
            MagicMock(device='/dev/sda1', mountpoint='/', fstype='ext4', opts='rw,relatime'),
            MagicMock(device='/dev/sda2', mountpoint='/home', fstype='ext4', opts='rw,relatime')
        ]
        mock_disk_usage.side_effect = [
            MagicMock(total=500000000000, used=250000000000, free=250000000000, percent=50.0),
            MagicMock(total=1000000000000, used=500000000000, free=500000000000, percent=50.0)
        ]
        mock_net_io.return_value = MagicMock(bytes_sent=123456, bytes_recv=654321)

        response = monitor_system_resources(1.0)
        mock_cpu_percent.assert_called_once_with(interval=1.0)
        mock_virtual_memory.assert_called_once()
        mock_swap_memory.assert_called_once()
        mock_disk_partitions.assert_called_once()
        mock_disk_usage.assert_any_call('/')
        mock_disk_usage.assert_any_call('/home')
        mock_net_io.assert_called_once()

        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNone(response["error"])
        self.assertIn("resources", response["output"])
        resources = response["output"]["resources"]
        self.assertEqual(resources["cpu_percent"], 15.0)
        self.assertEqual(resources["virtual_memory"]["percent"], 50.0)
        self.assertEqual(resources["swap_memory"]["percent"], 25.0)
        self.assertIn('/', resources["disk_usage"])
        self.assertIn('/home', resources["disk_usage"])
        self.assertIn('bytes_sent', resources["network_io"])
        self.assertIn('bytes_recv', resources["network_io"])

    @patch('psutil.cpu_percent', side_effect=Exception("Mocked exception"))
    def test_monitor_system_resources_unexpected_error(self, mock_cpu_percent):
        response = monitor_system_resources(1.0)
        mock_cpu_percent.assert_called_once_with(interval=1.0)
        self.assertEqual(response["error_code"], "FAILED_TO_MONITOR_RESOURCES")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to monitor system resources: Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()