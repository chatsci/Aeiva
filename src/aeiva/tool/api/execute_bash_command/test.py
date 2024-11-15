import unittest
from execute_bash_command.api import execute_bash_command


class TestExecuteBashCommand(unittest.TestCase):
    def test_valid_command(self):
        response = execute_bash_command(command="echo Hello, World!")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIn("Hello, World!", response["output"]["stdout"])

    def test_empty_command(self):
        response = execute_bash_command(command="")
        self.assertEqual(response["error_code"], "INVALID_COMMAND")
        self.assertEqual(response["error"], "Command cannot be empty.")

    def test_restart_session(self):
        response = execute_bash_command(command="echo Restart Test", restart=True)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIn("Restart Test", response["output"]["stdout"])

    def test_non_existent_command(self):
        response = execute_bash_command(command="non_existent_command")
        self.assertEqual(response["error_code"], "EXECUTION_FAILED")
        self.assertIn("command not found", response["output"]["stderr"])

    def test_error_handling(self):
        response = execute_bash_command(command="exit 1")
        self.assertEqual(response["output"]["exit_code"], 1)
        self.assertEqual(response["error_code"], "SUCCESS")


if __name__ == "__main__":
    unittest.main()