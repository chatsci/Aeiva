import unittest
from calculator.api import calculator


class TestCalculator(unittest.TestCase):
    def test_valid_operations(self):
        response = calculator("200*7")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"]["result"], "1400")

        response = calculator("5000/2*10")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertEqual(response["output"]["result"], "25000.0")

    def test_empty_operation(self):
        response = calculator("")
        self.assertEqual(response["error_code"], "INVALID_OPERATION")
        self.assertEqual(response["error"], "Operation cannot be empty.")

    def test_syntax_error(self):
        response = calculator("200*")
        self.assertEqual(response["error_code"], "SYNTAX_ERROR")
        self.assertEqual(response["error"], "Invalid mathematical expression.")

    def test_division_by_zero(self):
        response = calculator("10/0")
        self.assertEqual(response["error_code"], "DIVISION_BY_ZERO")
        self.assertEqual(response["error"], "Division by zero is not allowed.")

    def test_unexpected_error(self):
        response = calculator("math.sqrt(16)")
        self.assertEqual(response["error_code"], "UNEXPECTED_ERROR")
        self.assertIn("Unexpected error", response["error"])


if __name__ == "__main__":
    unittest.main()