# toolkit/system_toolkit/get_package_root/test.py

import unittest
import sys
import os
from toolkit.system_toolkit.get_package_root.api import get_package_root

class TestGetPackageRoot(unittest.TestCase):
    def test_existing_package(self):
        # Test with a standard library package
        response = get_package_root("os")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIsNotNone(response["output"]["package_root"])
        self.assertTrue(os.path.isdir(response["output"]["package_root"]))
    
    def test_nonexistent_package(self):
        # Test with a package that doesn't exist
        response = get_package_root("nonexistent_package_xyz")
        self.assertEqual(response["error_code"], "PACKAGE_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("Cannot find package", response["error"])
    
    def test_invalid_input(self):
        # Test with invalid input types
        with self.assertRaises(TypeError):
            get_package_root(None)  # package_name should be a string
    
    def test_import_error(self):
        # Simulate an ImportError by using a malformed package name
        response = get_package_root("sys.nonexistent_module")
        self.assertEqual(response["error_code"], "PACKAGE_NOT_FOUND")
        self.assertIsNone(response["output"])
        self.assertIn("Cannot find package", response["error"])
    
    def test_unexpected_error(self):
        # Simulate an unexpected error by mocking importlib.util.find_spec
        original_find_spec = importlib.util.find_spec
        def mock_find_spec(name):
            raise Exception("Mocked unexpected exception")
        import importlib.util
        importlib.util.find_spec = mock_find_spec
        
        response = get_package_root("os")
        self.assertEqual(response["error_code"], "UNEXPECTED_ERROR")
        self.assertIsNone(response["output"])
        self.assertIn("An unexpected error occurred", response["error"])
        
        # Restore the original function
        importlib.util.find_spec = original_find_spec

if __name__ == "__main__":
    unittest.main()