from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from typing import Iterable, Optional


_RUNTIME_CHECK_SNIPPET = (
    "import importlib.util,sys;"
    "ok=bool(importlib.util.find_spec('PySide6')) and "
    "bool(importlib.util.find_spec('PySide6.QtWebEngineWidgets'));"
    "sys.exit(0 if ok else 1)"
)

_cached_desktop_python: Optional[str] = ...  # sentinel: ... = not yet resolved


def _iter_project_venv_candidates(start: Path) -> Iterable[str]:
    for base in (start, *start.parents):
        candidate = base / ".venv" / "bin" / "python"
        if candidate.is_file():
            yield str(candidate)
            return


def _python_has_desktop_runtime(executable: str) -> bool:
    try:
        result = subprocess.run(
            [executable, "-c", _RUNTIME_CHECK_SNIPPET],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2.0,
            check=False,
        )
    except Exception:
        return False
    return result.returncode == 0


def resolve_desktop_python(*, current_executable: Optional[str] = None) -> Optional[str]:
    """
    Resolve a Python executable that can launch `aeiva.metaui.desktop_client`.

    Result is cached for the process lifetime — the available interpreters
    and their installed packages do not change while the process is running.

    Preference order:
    1) current process interpreter
    2) nearest project `.venv/bin/python` (from cwd upward)
    """
    global _cached_desktop_python
    if _cached_desktop_python is not ...:
        return _cached_desktop_python

    current = str(current_executable or sys.executable)
    seen: set[str] = set()
    candidates: list[str] = [current]
    candidates.extend(_iter_project_venv_candidates(Path.cwd()))

    for executable in candidates:
        if executable in seen:
            continue
        seen.add(executable)
        if _python_has_desktop_runtime(executable):
            _cached_desktop_python = executable
            return executable

    _cached_desktop_python = None
    return None
