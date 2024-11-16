# toolkit/system_toolkit/get_user_home_path/test.py

import unittest
import platform
import os
from pathlib import Path
from toolkit.system_toolkit.get_user_home_path.api import get_user_home_path

class TestGetUserHomePath(unittest.TestCase):
    def test_successful_retrieval(self):
        response = get_user_home_path()
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNotNone(response["output"]["user_home"])
        self.assertTrue(Path(response["output"]["user_home"]).is_dir())
    
    def test_invalid_home_directory(self):
        # Temporarily mock os.path.isdir to return False
        original_isdir = os.path.isdir
        os.path.isdir = lambda path: False
        try:
            response = get_user_home_path()
            self.assertEqual(response["error_code"], "INVALID_HOME_DIRECTORY")
            self.assertIsNone(response["output"])
            self.assertIn("Determined home directory does not exist", response["error"])
        finally:
            os.path.isdir = original_isdir
    
    def test_unexpected_error(self):
        # Simulate an unexpected error by mocking platform.system
        original_system = platform.system
        platform.system = lambda: "UnknownOS"
        try:
            response = get_user_home_path()
            self.assertEqual(response["error_code"], "SUCCESS")
            # Even for unknown OS, it falls back to expanduser
            self.assertIsNotNone(response["output"]["user_home"])
            self.assertTrue(Path(response["output"]["user_home"]).is_dir())
        finally:
            platform.system = original_system

if __name__ == "__main__":
    unittest.main()