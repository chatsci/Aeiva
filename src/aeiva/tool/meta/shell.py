"""
Shell Tool: Execute shell commands.

The most fundamental meta tool - enables all system interactions.
"""

import asyncio
from typing import Dict, Any, Optional

from ..decorator import tool
from ..capability import Capability


@tool(
    description="Execute a shell command and return output",
    capabilities=[Capability.SHELL],
)
async def shell(
    command: str,
    timeout: int = 30,
    cwd: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a shell command asynchronously.

    Args:
        command: The shell command to execute.
        timeout: Maximum execution time in seconds.
        cwd: Working directory for command execution.

    Returns:
        Dictionary with stdout, stderr, and return_code.
    """
    if isinstance(cwd, str) and not cwd.strip():
        cwd = None
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )
        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "return_code": process.returncode,
            "success": process.returncode == 0,
        }
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return {
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "return_code": -1,
            "success": False,
        }
    except OSError as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "return_code": -1,
            "success": False,
        }
