import base64
import platform
import shutil
import subprocess
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple, Dict
from uuid import uuid4


class ActionType(str, Enum):
    KEY = "key"
    TYPE = "type"
    MOUSE_MOVE = "mouse_move"
    LEFT_CLICK = "left_click"
    LEFT_CLICK_DRAG = "left_click_drag"
    RIGHT_CLICK = "right_click"
    MIDDLE_CLICK = "middle_click"
    DOUBLE_CLICK = "double_click"
    SCREENSHOT = "screenshot"
    CURSOR_POSITION = "cursor_position"


def operate_computer(action: str, text: Optional[str] = None, coordinate: Optional[Tuple[int, int]] = None) -> Dict:
    try:
        # Validate action
        if action not in ActionType.__members__.values():
            return _error(f"Unsupported action: {action}", "INVALID_ACTION")

        # Initialize platform-dependent tools
        os_type = platform.system()
        mouse_tool = _get_mouse_tool(os_type)
        screenshot_tool = _get_screenshot_tool(os_type)

        if action == ActionType.SCREENSHOT.value:
            return _take_screenshot(screenshot_tool)

        if action in [ActionType.MOUSE_MOVE.value, ActionType.LEFT_CLICK_DRAG.value]:
            if not coordinate:
                return _error("Coordinate is required for this action", "INVALID_COORDINATE")
            return _mouse_action(action, coordinate, mouse_tool, os_type)

        if action in [ActionType.KEY.value, ActionType.TYPE.value]:
            if not text:
                return _error("Text is required for this action", "INVALID_INPUT")
            return _keyboard_action(action, text, mouse_tool)

        if action == ActionType.CURSOR_POSITION.value:
            return _get_cursor_position(os_type)

        return _error(f"Unsupported action: {action}", "INVALID_ACTION")

    except Exception as e:
        return {
            "output": None,
            "error": str(e),
            "error_code": "EXECUTION_FAILED"
        }


def _get_mouse_tool(os_type: str) -> Optional[str]:
    if os_type == "Darwin":
        return shutil.which("cliclick")
    elif os_type == "Linux":
        return shutil.which("xdotool")
    raise NotImplementedError(f"Unsupported OS: {os_type}")


def _get_screenshot_tool(os_type: str) -> Optional[str]:
    if os_type == "Darwin":
        return "screencapture"
    elif os_type == "Linux":
        return "import"
    raise NotImplementedError(f"Unsupported OS: {os_type}")


def _mouse_action(action: str, coordinate: Tuple[int, int], mouse_tool: str, os_type: str) -> Dict:
    x, y = coordinate
    if action == ActionType.MOUSE_MOVE.value:
        cmd = _get_mouse_move_cmd(mouse_tool, x, y, os_type)
    elif action == ActionType.LEFT_CLICK_DRAG.value:
        cmd = _get_mouse_drag_cmd(mouse_tool, x, y, os_type)
    else:
        return _error(f"Unsupported mouse action: {action}", "INVALID_ACTION")

    _execute_command(cmd)
    return {"output": "Mouse action executed successfully", "error": None, "error_code": "SUCCESS"}


def _keyboard_action(action: str, text: str, mouse_tool: str) -> Dict:
    if action == ActionType.KEY.value:
        cmd = f"{mouse_tool} kp:{text}"
    elif action == ActionType.TYPE.value:
        cmd = f"{mouse_tool} t:{text}"
    else:
        return _error(f"Unsupported keyboard action: {action}", "INVALID_ACTION")

    _execute_command(cmd)
    return {"output": "Keyboard action executed successfully", "error": None, "error_code": "SUCCESS"}


def _get_cursor_position(os_type: str) -> Dict:
    try:
        if os_type == "Darwin":
            cmd = "cliclick p:"
        elif os_type == "Linux":
            cmd = "xdotool getmouselocation"
        else:
            return _error(f"Unsupported OS: {os_type}", "NOT_SUPPORTED")

        output = _execute_command(cmd)
        return {"output": output, "error": None, "error_code": "SUCCESS"}
    except Exception as e:
        return _error(str(e), "EXECUTION_FAILED")


def _take_screenshot(screenshot_tool: str) -> Dict:
    path = Path(f"/tmp/screenshot_{uuid4().hex}.png")
    cmd = f"{screenshot_tool} {path}"

    _execute_command(cmd)
    if path.exists():
        with open(path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode()
        return {"output": "Screenshot taken successfully", "error": None, "error_code": "SUCCESS", "base64_image": base64_image}
    return _error("Failed to take screenshot", "EXECUTION_FAILED")


def _get_mouse_move_cmd(mouse_tool: str, x: int, y: int, os_type: str) -> str:
    if os_type == "Darwin":
        return f"{mouse_tool} m:{x},{y}"
    elif os_type == "Linux":
        return f"xdotool mousemove {x} {y}"
    raise NotImplementedError(f"Unsupported OS: {os_type}")


def _get_mouse_drag_cmd(mouse_tool: str, x: int, y: int, os_type: str) -> str:
    if os_type == "Darwin":
        return f"{mouse_tool} dd:{x},{y} du:{x},{y}"
    elif os_type == "Linux":
        return f"xdotool mousemove {x} {y} mousedown 1 mousemove {x} {y} mouseup 1"
    raise NotImplementedError(f"Unsupported OS: {os_type}")


def _execute_command(cmd: str) -> str:
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode())
    return result.stdout.decode()


def _error(message: str, error_code: str) -> Dict:
    return {"output": None, "error": message, "error_code": error_code}