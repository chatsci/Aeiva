# toolkit/system_toolkit/set_env_var/test.py

import unittest
from unittest.mock import patch
from toolkit.system_toolkit.set_env_var.api import set_env_var

class TestSetEnvVar(unittest.TestCase):
    @patch.dict('os.environ', {}, clear=True)
    def test_set_env_var_success(self):
        response = set_env_var("NEW_VAR", "new_value")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"], "Environment variable 'NEW_VAR' set to 'new_value'.")
        self.assertIsNone(response["error"])
        self.assertEqual(os.environ["NEW_VAR"], "new_value")

    @patch('os.environ.__setitem__', side_effect=Exception("Mocked exception"))
    def test_set_env_var_failed_to_set(self, mock_setitem):
        response = set_env_var("ANY_VAR", "any_value")
        mock_setitem.assert_called_with("ANY_VAR", "any_value")
        self.assertEqual(response["error_code"], "FAILED_TO_SET_ENV_VAR")
        self.assertIsNone(response["output"])
        self.assertIn("Failed to set environment variable 'ANY_VAR': Mocked exception", response["error"])

    def test_set_env_var_unexpected_error(self):
        # For example, passing None as var_name, which should raise a TypeError
        with self.assertRaises(TypeError):
            set_env_var(None, "value")

if __name__ == "__main__":
    unittest.main()