import unittest
from operate_computer.api import operate_computer, ActionType


class TestOperateComputer(unittest.TestCase):
    def test_mouse_move(self):
        response = operate_computer(action=ActionType.MOUSE_MOVE.value, coordinate=(100, 200))
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIn("Mouse action executed successfully", response["output"])

    def test_invalid_mouse_move(self):
        response = operate_computer(action=ActionType.MOUSE_MOVE.value, coordinate=None)
        self.assertEqual(response["error_code"], "INVALID_COORDINATE")
        self.assertIn("Coordinate is required for this action", response["error"])

    def test_key_action(self):
        response = operate_computer(action=ActionType.KEY.value, text="ctrl+a")
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIn("Keyboard action executed successfully", response["output"])

    def test_invalid_key_action(self):
        response = operate_computer(action=ActionType.KEY.value, text=None)
        self.assertEqual(response["error_code"], "INVALID_INPUT")
        self.assertIn("Text is required for this action", response["error"])

    def test_screenshot(self):
        response = operate_computer(action=ActionType.SCREENSHOT.value)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIn("Screenshot taken successfully", response["output"])
        self.assertIsNotNone(response["base64_image"])

    def test_cursor_position(self):
        response = operate_computer(action=ActionType.CURSOR_POSITION.value)
        self.assertEqual(response["error_code"], "SUCCESS")
        self.assertIn("X=", response["output"])
        self.assertIn("Y=", response["output"])

    def test_invalid_action(self):
        response = operate_computer(action="invalid_action")
        self.assertEqual(response["error_code"], "INVALID_ACTION")
        self.assertIn("Unsupported action", response["error"])

    def test_action_with_unsupported_os(self):
        import platform
        original_os = platform.system
        platform.system = lambda: "UnsupportedOS"
        response = operate_computer(action=ActionType.MOUSE_MOVE.value, coordinate=(100, 200))
        self.assertEqual(response["error_code"], "NOT_SUPPORTED")
        self.assertIn("Unsupported OS", response["error"])
        platform.system = original_os


if __name__ == "__main__":
    unittest.main()