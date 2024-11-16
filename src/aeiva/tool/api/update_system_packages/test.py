# toolkit/system_toolkit/update_system_packages/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.system_toolkit.update_system_packages.api import update_system_packages

class TestUpdateSystemPackages(unittest.TestCase):
    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run')
    def test_update_system_packages_success_windows(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="All packages upgraded successfully.", stderr="")
        response = update_system_packages()
        mock_run.assert_called_with('winget upgrade --all', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "All packages upgraded successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Darwin')
    @patch('subprocess.run')
    def test_update_system_packages_success_mac(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="brew update && brew upgrade executed successfully.", stderr="")
        response = update_system_packages()
        mock_run.assert_called_with('brew update && brew upgrade', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "brew update && brew upgrade executed successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('platform.linux_distribution', return_value=('Ubuntu', '20.04', 'focal'))
    @patch('subprocess.run')
    def test_update_system_packages_success_linux_ubuntu(self, mock_run, mock_distro, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="sudo apt-get update && sudo apt-get upgrade -y executed successfully.", stderr="")
        response = update_system_packages()
        mock_run.assert_called_with('sudo apt-get update && sudo apt-get upgrade -y', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "sudo apt-get update && sudo apt-get upgrade -y executed successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('platform.linux_distribution', return_value=('Fedora', '33', ''))
    @patch('subprocess.run')
    def test_update_system_packages_success_linux_fedora(self, mock_run, mock_distro, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="sudo dnf upgrade -y executed successfully.", stderr="")
        response = update_system_packages()
        mock_run.assert_called_with('sudo dnf upgrade -y', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "sudo dnf upgrade -y executed successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('platform.linux_distribution', return_value=('Arch', 'rolling', ''))
    def test_update_system_packages_unsupported_distribution(self, mock_distro, mock_system):
        response = update_system_packages()
        self.assertEqual(response["error_code"], "UNSUPPORTED_DISTRIBUTION")
        self.assertIsNone(response["output"])
        self.assertIn("Unsupported Linux distribution: arch", response["error"])

    @patch('platform.system', return_value='UnknownOS')
    def test_update_system_packages_unsupported_os(self, mock_system):
        response = update_system_packages()
        self.assertEqual(response["error_code"], "UNSUPPORTED_OS")
        self.assertIsNone(response["output"])
        self.assertIn("Unsupported operating system: UnknownOS", response["error"])

    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run', side_effect=Exception("Mocked exception"))
    def test_update_system_packages_unexpected_error(self, mock_run, mock_system):
        response = update_system_packages()
        mock_run.assert_called_with('winget upgrade --all', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "FAILED_TO_UPDATE_PACKAGES")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to update system packages: Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()