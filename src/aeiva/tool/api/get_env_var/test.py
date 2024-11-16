# toolkit/system_toolkit/get_env_var/test.py

import unittest
from unittest.mock import patch
from toolkit.system_toolkit.get_env_var.api import get_env_var

class TestGetEnvVar(unittest.TestCase):
    @patch.dict('os.environ', {'TEST_VAR': 'test_value'})
    def test_get_env_var_success(self):
        response = get_env_var("TEST_VAR")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"]["value"], "test_value")
        self.assertIsNone(response["error"])

    def test_get_env_var_not_found(self):
        response = get_env_var("NONEXISTENT_VAR")
        self.assertEqual(response["error_code"], "ENV_VAR_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("Environment variable 'NONEXISTENT_VAR' not found.", response["error"])

    @patch('os.environ.get', side_effect=Exception("Mocked exception"))
    def test_get_env_var_failed_to_get(self, mock_env_get):
        response = get_env_var("ANY_VAR")
        mock_env_get.assert_called_with("ANY_VAR")
        self.assertEqual(response["error_code"], "FAILED_TO_GET_ENV_VAR")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to get environment variable 'ANY_VAR': Mocked exception", response["error"])

if __name__ == "__main__":
    unittest.main()