# toolkit/system_toolkit/install_package/test.py

import unittest
from unittest.mock import patch, MagicMock
from toolkit.system_toolkit.install_package.api import install_package
import platform

class TestInstallPackage(unittest.TestCase):
    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run')
    def test_install_python_package_success(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="Successfully installed package.", stderr="")
        response = install_package("requests", "python")
        mock_run.assert_called_with(['pip', 'install', 'requests'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "Successfully installed package.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Darwin')
    @patch('subprocess.run')
    def test_install_system_package_success_mac(self, mock_run, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="brew install package_name executed successfully.", stderr="")
        response = install_package("wget", "system")
        mock_run.assert_called_with(['brew', 'install', 'wget'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "brew install package_name executed successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('platform.linux_distribution', return_value=('Ubuntu', '20.04', 'focal'))
    @patch('subprocess.run')
    def test_install_system_package_success_linux_ubuntu(self, mock_run, mock_distro, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="sudo apt-get install -y package_name executed successfully.", stderr="")
        response = install_package("vim", "system")
        mock_run.assert_called_with(['sudo', 'apt-get', 'install', '-y', 'vim'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "sudo apt-get install -y package_name executed successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('platform.linux_distribution', return_value=('Fedora', '33', ''))
    @patch('subprocess.run')
    def test_install_system_package_success_linux_fedora(self, mock_run, mock_distro, mock_system):
        mock_run.return_value = MagicMock(returncode=0, stdout="sudo dnf install -y package_name executed successfully.", stderr="")
        response = install_package("vim", "system")
        mock_run.assert_called_with(['sudo', 'dnf', 'install', '-y', 'vim'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "sudo dnf install -y package_name executed successfully.")
        self.assertIsNone(response["error"])

    @patch('platform.system', return_value='Linux')
    @patch('platform.linux_distribution', return_value=('Arch', 'rolling', ''))
    def test_install_system_package_unsupported_distro(self, mock_distro, mock_system):
        response = install_package("vim", "system")
        self.assertEqual(response["error_code"], "UNSUPPORTED_DISTRIBUTION")
        self.assertIsNone(response["output"])
        self.assertIn("Unsupported Linux distribution: arch", response["error"])

    @patch('platform.system', return_value='UnknownOS')
    def test_install_system_package_unsupported_os(self, mock_system):
        response = install_package("vim", "system")
        self.assertEqual(response["error_code"], "UNSUPPORTED_OS")
        self.assertIsNone(response["output"])
        self.assertIn("Unsupported operating system: UnknownOS", response["error"])

    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run', side_effect=Exception("Mocked exception"))
    def test_install_package_unexpected_error(self, mock_run, mock_system):
        response = install_package("requests", "python")
        mock_run.assert_called_with(['pip', 'install', 'requests'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(response["error_code"], "FAILED_TO_INSTALL_PACKAGE")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to install package 'requests': Mocked exception", response["error"])

    def test_install_package_unsupported_package_type(self):
        response = install_package("vim", "unknown_type")
        self.assertEqual(response["error_code"], "UNSUPPORTED_PACKAGE_TYPE")
        self.assertIsNone(response["output"])
        self.assertIn("Unsupported package type: unknown_type", response["error"])

if __name__ == "__main__":
    unittest.main()