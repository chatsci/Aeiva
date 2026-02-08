from __future__ import annotations

import base64
import os
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_name(name: str) -> str:
    normalized = _SAFE_NAME_RE.sub("_", (name or "").strip())
    return normalized.strip("._") or "upload.bin"


@dataclass(frozen=True)
class UploadStoreConfig:
    base_dir: Path
    max_file_bytes: int = 8 * 1024 * 1024
    max_total_bytes: int = 24 * 1024 * 1024
    max_files_per_event: int = 12
    retention_seconds: int = 7 * 24 * 60 * 60
    max_session_dirs: int = 1024
    cleanup_interval_seconds: int = 300


class UploadStore:
    """
    Persist uploaded file payloads from MetaUI desktop events into sandboxed storage.
    """

    def __init__(self, config: UploadStoreConfig) -> None:
        self.config = config
        self.config.base_dir.mkdir(parents=True, exist_ok=True)
        self._last_cleanup_at = 0.0

    def _time_now(self) -> float:
        return time.time()

    def _list_session_dirs(self) -> List[Path]:
        base = self.config.base_dir
        if not base.exists():
            return []
        return [
            path
            for path in base.iterdir()
            if path.is_dir()
        ]

    def _maybe_cleanup(self) -> None:
        interval = max(0, int(self.config.cleanup_interval_seconds))
        if interval == 0:
            self.cleanup(force=True)
            return
        now = self._time_now()
        if (now - self._last_cleanup_at) < float(interval):
            return
        self.cleanup(force=True)

    def cleanup(self, *, force: bool = False) -> Dict[str, Any]:
        now = self._time_now()
        if not force:
            interval = max(0, int(self.config.cleanup_interval_seconds))
            if interval > 0 and (now - self._last_cleanup_at) < float(interval):
                return {"success": True, "deleted_count": 0, "scanned_count": 0}
        self._last_cleanup_at = now

        session_dirs = self._list_session_dirs()
        retention_seconds = max(0, int(self.config.retention_seconds))
        max_session_dirs = max(1, int(self.config.max_session_dirs))

        stale: set[Path] = set()
        if retention_seconds > 0:
            for path in session_dirs:
                try:
                    age = now - path.stat().st_mtime
                except Exception:
                    continue
                if age > float(retention_seconds):
                    stale.add(path)

        to_delete: set[Path] = set(stale)
        remaining = [path for path in session_dirs if path not in stale]
        overflow = len(remaining) - max_session_dirs
        if overflow > 0:
            remaining_sorted = sorted(
                remaining,
                key=lambda path: path.stat().st_mtime if path.exists() else 0.0,
            )
            to_delete.update(remaining_sorted[:overflow])

        deleted: List[str] = []
        for path in sorted(to_delete, key=lambda item: str(item)):
            try:
                shutil.rmtree(path)
                deleted.append(str(path))
            except Exception:
                continue

        return {
            "success": True,
            "scanned_count": len(session_dirs),
            "deleted_count": len(deleted),
            "deleted": deleted,
        }

    def _prepare_event_dir(self, *, session_id: str, event_id: str) -> tuple[Path | None, str | None]:
        safe_session = _safe_name(session_id or "default")
        safe_event = _safe_name(event_id or "event")
        raw_base = self.config.base_dir
        session_dir = raw_base / safe_session
        event_dir = session_dir / safe_event

        for candidate in (session_dir, event_dir):
            if candidate.exists() and candidate.is_symlink():
                return None, f"upload path contains symlink: {candidate}"

        try:
            event_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return None, f"failed to create upload directory: {exc}"

        for candidate in (session_dir, event_dir):
            if candidate.exists() and candidate.is_symlink():
                return None, f"upload path contains symlink: {candidate}"

        try:
            base_dir = raw_base.resolve()
            resolved_event_dir = event_dir.resolve()
            resolved_event_dir.relative_to(base_dir)
        except Exception:
            return None, "resolved upload path escapes sandbox"
        return resolved_event_dir, None

    @staticmethod
    def _open_event_dir_fd(event_dir: Path) -> int | None:
        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= getattr(os, "O_DIRECTORY")
        try:
            return os.open(str(event_dir), flags)
        except Exception:
            return None

    @staticmethod
    def _write_file_bytes(*, event_dir: Path, dir_fd: int | None, file_name: str, raw: bytes) -> str | None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= getattr(os, "O_NOFOLLOW")

        supports_dir_fd = os.open in getattr(os, "supports_dir_fd", set())
        if dir_fd is not None and supports_dir_fd:
            try:
                fd = os.open(file_name, flags, 0o600, dir_fd=dir_fd)
                with os.fdopen(fd, "wb") as handle:
                    handle.write(raw)
                return None
            except Exception as exc:
                return str(exc)

        path = event_dir / file_name
        if path.exists() and path.is_symlink():
            return "target path is symlink"
        try:
            fd = os.open(str(path), flags, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
            return None
        except Exception as exc:
            return str(exc)

    def persist_files(
        self,
        *,
        files: List[Dict[str, Any]],
        session_id: str,
        event_id: str,
    ) -> Dict[str, Any]:
        self._maybe_cleanup()
        if not isinstance(files, list):
            return {"success": False, "error": "upload payload must contain a files list"}
        if len(files) > self.config.max_files_per_event:
            return {
                "success": False,
                "error": f"too many files in one event: {len(files)} > {self.config.max_files_per_event}",
            }

        event_dir, event_error = self._prepare_event_dir(session_id=session_id, event_id=event_id)
        if event_dir is None:
            return {"success": False, "error": event_error or "failed to prepare upload directory"}

        total_bytes = 0
        stored: List[Dict[str, Any]] = []
        dir_fd = self._open_event_dir_fd(event_dir)
        try:
            for index, entry in enumerate(files):
                if not isinstance(entry, dict):
                    return {"success": False, "error": f"file entry #{index} must be object"}
                name = _safe_name(str(entry.get("name") or f"file_{index}"))
                content_b64 = entry.get("content_base64")
                if not isinstance(content_b64, str) or not content_b64:
                    return {"success": False, "error": f"file '{name}' missing content_base64"}
                try:
                    raw = base64.b64decode(content_b64, validate=True)
                except Exception:
                    return {"success": False, "error": f"file '{name}' has invalid base64 payload"}

                size = len(raw)
                if size > self.config.max_file_bytes:
                    return {
                        "success": False,
                        "error": f"file '{name}' exceeds per-file limit ({size} > {self.config.max_file_bytes})",
                    }

                total_bytes += size
                if total_bytes > self.config.max_total_bytes:
                    return {
                        "success": False,
                        "error": (
                            f"event exceeds total upload limit ({total_bytes} > {self.config.max_total_bytes})"
                        ),
                    }

                file_name = f"{index:02d}_{name}"
                write_error = self._write_file_bytes(
                    event_dir=event_dir,
                    dir_fd=dir_fd,
                    file_name=file_name,
                    raw=raw,
                )
                if write_error is not None:
                    return {
                        "success": False,
                        "error": f"cannot write file '{name}': {write_error}",
                    }
                path = event_dir / file_name
                stored.append(
                    {
                        "name": name,
                        "size": size,
                        "mime": entry.get("mime") or "application/octet-stream",
                        "path": str(path),
                    }
                )
        finally:
            if dir_fd is not None:
                try:
                    os.close(dir_fd)
                except Exception:
                    pass

        return {
            "success": True,
            "count": len(stored),
            "total_bytes": total_bytes,
            "files": stored,
            "event_dir": str(event_dir),
        }
