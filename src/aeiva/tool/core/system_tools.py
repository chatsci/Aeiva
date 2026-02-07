"""
System Tools: Safe, structured OS helpers.

These are narrow, explicit tools to reduce reliance on raw shell.
"""

import asyncio
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Dict
from urllib.parse import urlparse

from ..decorator import tool
from ..capability import Capability


@tool(
    description="Locate a command in PATH (safe wrapper around `command -v`).",
    capabilities=[Capability.SHELL],
)
async def system_which(command: str) -> Dict[str, Any]:
    if not isinstance(command, str) or not command.strip():
        return {"success": False, "error": "command is required"}
    normalized = command.strip()
    resolved = shutil.which(normalized)
    return {
        "success": bool(resolved),
        "command": normalized,
        "path": resolved,
    }


@tool(
    description="Open a URL, file, or folder with the system default app. Prefer this over raw shell open/xdg-open.",
    capabilities=[Capability.SHELL],
)
async def system_open(path: str) -> Dict[str, Any]:
    target = _normalize_target(path)
    if not target:
        return {"success": False, "error": "path is required"}

    opener_cmd = _opener_command(target)
    if opener_cmd is None:
        return {
            "success": False,
            "error": f"Unsupported platform for open: {sys.platform}",
            "target": target,
        }

    try:
        process = await asyncio.create_subprocess_exec(
            *opener_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
    except FileNotFoundError as exc:
        return {
            "success": False,
            "error": str(exc),
            "target": target,
            "command": opener_cmd,
        }
    except OSError as exc:
        return {
            "success": False,
            "error": str(exc),
            "target": target,
            "command": opener_cmd,
        }

    stderr_text = stderr.decode("utf-8", errors="replace").strip()
    if process.returncode != 0:
        return {
            "success": False,
            "error": stderr_text or f"open command failed with exit code {process.returncode}",
            "target": target,
            "command": opener_cmd,
            "return_code": process.returncode,
        }

    return {
        "success": True,
        "target": target,
        "command": opener_cmd,
    }


@tool(
    description="Show a desktop notification.",
    capabilities=[Capability.SHELL],
)
async def system_notify(title: str, message: str) -> Dict[str, Any]:
    clean_title = str(title or "").strip()
    clean_message = str(message or "").strip()
    if not clean_title and not clean_message:
        return {"success": False, "error": "title or message is required"}

    if sys.platform.startswith("darwin"):
        script = (
            'display notification "{msg}" with title "{title}"'
            .format(msg=clean_message.replace('"', '\\"'), title=clean_title.replace('"', '\\"'))
        )
        cmd = ["osascript", "-e", script]
    else:
        # Keep behavior explicit and deterministic on unsupported platforms.
        return {
            "success": False,
            "error": f"Notifications are currently implemented for macOS only (platform={sys.platform}).",
        }

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
    except Exception as exc:
        return {"success": False, "error": str(exc), "command": cmd}

    stderr_text = stderr.decode("utf-8", errors="replace").strip()
    if process.returncode != 0:
        return {
            "success": False,
            "error": stderr_text or f"notify command failed with exit code {process.returncode}",
            "command": cmd,
            "return_code": process.returncode,
        }

    return {"success": True, "command": cmd}


def _normalize_target(path: str) -> str:
    if not isinstance(path, str):
        return ""
    raw = path.strip()
    if not raw:
        return ""

    if _looks_like_url(raw):
        return raw

    expanded = os.path.expandvars(os.path.expanduser(raw))
    candidate = Path(expanded)
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()

    if candidate.exists():
        return str(candidate)

    remapped = _remap_sandbox_path(candidate)
    if remapped is not None:
        return str(remapped)

    # Keep deterministic behavior for non-existing paths.
    return str(candidate)


def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https", "mailto", "file"}:
        return True
    return False


def _remap_sandbox_path(candidate: Path) -> Path | None:
    text = str(candidate)
    prefix = "/home/sandbox/"
    if not text.startswith(prefix):
        return None
    suffix = text[len(prefix):]
    options: list[Path] = []

    home = Path.home()
    options.append(home / suffix)
    user = os.getenv("USER") or os.getenv("USERNAME")
    if user:
        options.append(Path("/Users") / user / suffix)

    for option in options:
        if option.exists():
            return option
    return None


def _opener_command(target: str) -> list[str] | None:
    if sys.platform.startswith("darwin"):
        return ["open", target]
    if os.name == "nt":
        return ["cmd", "/c", "start", "", target]
    if sys.platform.startswith("linux"):
        return ["xdg-open", target]
    return None
