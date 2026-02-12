"""
Filesystem Tool: Universal file operations.

One meta tool for ALL file operations - read, write, list, delete, move, copy, etc.
"""

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from ..decorator import tool
from ..capability import Capability

try:
    import aiofiles
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False


@tool(
    description="Perform filesystem operations: read, write, list, delete, move, copy, mkdir, exists",
    capabilities=[Capability.FILESYSTEM],
)
async def filesystem(
    operation: str,
    path: str,
    content: Optional[str] = None,
    destination: Optional[str] = None,
    pattern: Optional[str] = None,
    recursive: bool = False,
    encoding: str = "utf-8",
    create_dirs: bool = True,
) -> Dict[str, Any]:
    """
    Universal filesystem tool for all file operations.

    Args:
        operation: Operation to perform: read, write, append, list, delete, move, copy, mkdir, exists, stat.
        path: Path to the file or directory.
        content: Content to write (for write/append operations).
        destination: Destination path (for move/copy operations).
        pattern: Glob pattern (for list operation).
        recursive: Recursive operation (for delete/list/copy).
        encoding: File encoding for text operations.
        create_dirs: Create parent directories if needed (for write/mkdir).

    Returns:
        Dictionary with operation result or error.
    """
    path = os.path.expanduser(path)

    operations = {
        "read": _read,
        "write": _write,
        "append": _append,
        "list": _list,
        "delete": _delete,
        "move": _move,
        "copy": _copy,
        "mkdir": _mkdir,
        "exists": _exists,
        "stat": _stat,
    }

    if operation not in operations:
        return {
            "success": False,
            "error": f"Unknown operation: {operation}. Valid: {list(operations.keys())}",
        }

    try:
        return await operations[operation](
            path=path,
            content=content,
            destination=destination,
            pattern=pattern,
            recursive=recursive,
            encoding=encoding,
            create_dirs=create_dirs,
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _read(path: str, encoding: str, **_) -> Dict[str, Any]:
    """Read file contents."""
    if not os.path.isfile(path):
        return {"success": False, "content": None, "error": f"File not found: {path}"}

    if HAS_AIOFILES:
        async with aiofiles.open(path, "r", encoding=encoding) as f:
            content = await f.read()
    else:
        content = await asyncio.to_thread(lambda: open(path, "r", encoding=encoding).read())

    return {"success": True, "content": content, "error": None}


async def _write(path: str, content: str, encoding: str, create_dirs: bool, **_) -> Dict[str, Any]:
    """Write content to file."""
    if content is None:
        return {"success": False, "error": "Content required for write operation"}

    if create_dirs:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    if HAS_AIOFILES:
        async with aiofiles.open(path, "w", encoding=encoding) as f:
            await f.write(content)
    else:
        await asyncio.to_thread(lambda: open(path, "w", encoding=encoding).write(content))

    return {"success": True, "path": path, "error": None}


async def _append(path: str, content: str, encoding: str, create_dirs: bool, **_) -> Dict[str, Any]:
    """Append content to file."""
    if content is None:
        return {"success": False, "error": "Content required for append operation"}

    if create_dirs:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    if HAS_AIOFILES:
        async with aiofiles.open(path, "a", encoding=encoding) as f:
            await f.write(content)
    else:
        await asyncio.to_thread(lambda: open(path, "a", encoding=encoding).write(content))

    return {"success": True, "path": path, "error": None}


async def _list(path: str, pattern: Optional[str], recursive: bool, **_) -> Dict[str, Any]:
    """List directory contents."""
    dir_path = Path(path)

    if not dir_path.is_dir():
        return {"success": False, "entries": [], "error": f"Not a directory: {path}"}

    if pattern:
        glob_method = dir_path.rglob if recursive else dir_path.glob
        entries = [str(p.relative_to(dir_path)) for p in glob_method(pattern)]
    elif recursive:
        entries = [str(p.relative_to(dir_path)) for p in dir_path.rglob("*")]
    else:
        entries = os.listdir(path)

    return {"success": True, "entries": sorted(entries), "error": None}


async def _delete(path: str, recursive: bool, **_) -> Dict[str, Any]:
    """Delete file or directory."""
    if not os.path.exists(path):
        return {"success": False, "error": f"Path not found: {path}"}

    if os.path.isdir(path):
        if recursive:
            shutil.rmtree(path)
        else:
            os.rmdir(path)
    else:
        os.remove(path)

    return {"success": True, "error": None}


async def _move(path: str, destination: Optional[str], **_) -> Dict[str, Any]:
    """Move file or directory."""
    if not destination:
        return {"success": False, "error": "Destination required for move operation"}
    if not os.path.exists(path):
        return {"success": False, "error": f"Source not found: {path}"}

    shutil.move(path, destination)
    return {"success": True, "destination": destination, "error": None}


async def _copy(path: str, destination: Optional[str], recursive: bool, **_) -> Dict[str, Any]:
    """Copy file or directory."""
    if not destination:
        return {"success": False, "error": "Destination required for copy operation"}
    if not os.path.exists(path):
        return {"success": False, "error": f"Source not found: {path}"}

    if os.path.isdir(path):
        if recursive:
            shutil.copytree(path, destination)
        else:
            return {"success": False, "error": "Use recursive=True to copy directories"}
    else:
        shutil.copy2(path, destination)

    return {"success": True, "destination": destination, "error": None}


async def _mkdir(path: str, create_dirs: bool, **_) -> Dict[str, Any]:
    """Create directory."""
    if create_dirs:
        os.makedirs(path, exist_ok=True)
    else:
        os.mkdir(path)

    return {"success": True, "path": path, "error": None}


async def _exists(path: str, **_) -> Dict[str, Any]:
    """Check if path exists."""
    exists = os.path.exists(path)
    is_file = os.path.isfile(path) if exists else False
    is_dir = os.path.isdir(path) if exists else False

    return {
        "success": True,
        "exists": exists,
        "is_file": is_file,
        "is_dir": is_dir,
        "error": None,
    }


async def _stat(path: str, **_) -> Dict[str, Any]:
    """Get file/directory statistics."""
    if not os.path.exists(path):
        return {"success": False, "error": f"Path not found: {path}"}

    stat = os.stat(path)
    return {
        "success": True,
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "created": stat.st_ctime,
        "is_file": os.path.isfile(path),
        "is_dir": os.path.isdir(path),
        "error": None,
    }
