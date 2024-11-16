# toolkit/system_toolkit/list_drives/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.system_toolkit.list_drives.api import list_drives
import psutil

class TestListDrives(unittest.TestCase):
    @patch('psutil.disk_partitions')
    def test_list_drives_success(self, mock_disk_partitions):
        mock_partition1 = MagicMock()
        mock_partition1.device = '/dev/sda1'
        mock_partition1.mountpoint = '/'
        mock_partition1.fstype = 'ext4'
        mock_partition1.opts = 'rw,relatime'

        mock_partition2 = MagicMock()
        mock_partition2.device = '/dev/sda2'
        mock_partition2.mountpoint = '/home'
        mock_partition2.fstype = 'ext4'
        mock_partition2.opts = 'rw,relatime'

        mock_disk_partitions.return_value = [mock_partition1, mock_partition2]

        response = list_drives()
        mock_disk_partitions.assert_called_once_with(all=False)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"]["drives"], [
            {
                "device": '/dev/sda1',
                "mountpoint": '/',
                "fstype": 'ext4',
                "opts": 'rw,relatime'
            },
            {
                "device": '/dev/sda2',
                "mountpoint": '/home',
                "fstype": 'ext4',
                "opts": 'rw,relatime'
            }
        ])
        self.assertIsNone(response["error"])

    @patch('psutil.disk_partitions', side_effect=Exception("Mocked exception"))
    def test_list_drives_failed(self, mock_disk_partitions):
        response = list_drives()
        mock_disk_partitions.assert_called_once_with(all=False)
        self.assertEqual(response["error_code"], "FAILED_TO_LIST_DRIVES")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to list drives: Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()