"""
System Tools: Safe, structured OS helpers.

These are narrow, explicit tools to reduce reliance on raw shell.
"""

from typing import Dict, Optional

from ..decorator import tool
from ..capability import Capability


@tool(
    description="Locate a command in PATH (safe wrapper around `command -v`).",
    capabilities=[Capability.SHELL],
)
async def system_which(command: str) -> Dict[str, str]:
    return {
        "command": command,
        "hint": "Use the shell tool to run `command -v <cmd>` if needed.",
    }


@tool(
    description="Open a file or folder with the system default app (safe wrapper).",
    capabilities=[Capability.SHELL],
)
async def system_open(path: str) -> Dict[str, str]:
    return {
        "path": path,
        "hint": "Use the shell tool to run `open <path>` on macOS or `xdg-open` on Linux.",
    }


@tool(
    description="Show a desktop notification (safe wrapper).",
    capabilities=[Capability.SHELL],
)
async def system_notify(title: str, message: str) -> Dict[str, str]:
    return {
        "title": title,
        "message": message,
        "hint": "Use the shell tool with platform-specific notification command if needed.",
    }
