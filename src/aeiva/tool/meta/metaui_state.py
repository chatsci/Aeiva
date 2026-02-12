from __future__ import annotations

from dataclasses import dataclass, field
import os
import subprocess
import threading
import time
from typing import Dict, List, Optional


DESKTOP_LAUNCH_COOLDOWN_SECONDS = 8.0
DESKTOP_CONNECT_GRACE_SECONDS = 45.0
DESKTOP_PENDING_ENV_VAR = "AEIVA_METAUI_DESKTOP_PENDING_UNTIL_MONO"


@dataclass
class DesktopLaunchState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    last_launch_attempt_mono: float = 0.0
    connect_grace_until_mono: float = 0.0
    launched_processes: List[subprocess.Popen] = field(default_factory=list)

    def mark_pending(self) -> None:
        grace_until = time.monotonic() + DESKTOP_CONNECT_GRACE_SECONDS
        with self.lock:
            self.connect_grace_until_mono = grace_until
        os.environ[DESKTOP_PENDING_ENV_VAR] = f"{grace_until:.6f}"

    def clear_pending(self) -> None:
        with self.lock:
            self.connect_grace_until_mono = 0.0
        os.environ.pop(DESKTOP_PENDING_ENV_VAR, None)

    @staticmethod
    def is_external_pending() -> bool:
        raw = os.getenv(DESKTOP_PENDING_ENV_VAR)
        if not raw:
            return False
        try:
            pending_until = float(raw)
        except Exception:
            return False
        return time.monotonic() < pending_until

    def try_claim_slot(self) -> bool:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_launch_attempt_mono
            in_grace_period = now < self.connect_grace_until_mono
            if self.is_external_pending():
                return False
            if elapsed < DESKTOP_LAUNCH_COOLDOWN_SECONDS or in_grace_period:
                return False
            self.last_launch_attempt_mono = now
            return True

    def register_process(self, process: subprocess.Popen) -> None:
        with self.lock:
            self.launched_processes.append(process)

    def prune_dead_processes(self) -> None:
        with self.lock:
            alive: List[subprocess.Popen] = []
            for process in self.launched_processes:
                try:
                    if process.poll() is None:
                        alive.append(process)
                except Exception:
                    continue
            self.launched_processes[:] = alive

    def live_process(self) -> Optional[subprocess.Popen]:
        self.prune_dead_processes()
        with self.lock:
            if not self.launched_processes:
                return None
            return self.launched_processes[-1]

    def cleanup_processes(self) -> None:
        with self.lock:
            processes = list(self.launched_processes)
            self.launched_processes.clear()
        for process in processes:
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=3)
            except Exception:
                try:
                    process.kill()
                    process.wait(timeout=2)
                except Exception:
                    pass

    def reset(self) -> None:
        with self.lock:
            self.last_launch_attempt_mono = 0.0
            self.connect_grace_until_mono = 0.0
            self.launched_processes.clear()
        os.environ.pop(DESKTOP_PENDING_ENV_VAR, None)


@dataclass
class ActiveUIState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    last_active_ui_id: Optional[str] = None
    last_active_ui_by_session: Dict[str, str] = field(default_factory=dict)

    def remember(self, *, ui_id: Optional[str], session_id: Optional[str]) -> None:
        resolved_ui_id = str(ui_id or "").strip()
        if not resolved_ui_id:
            return
        resolved_session_id = str(session_id or "").strip()
        with self.lock:
            self.last_active_ui_id = resolved_ui_id
            if resolved_session_id:
                self.last_active_ui_by_session[resolved_session_id] = resolved_ui_id

    def forget(self, *, ui_id: Optional[str]) -> None:
        target = str(ui_id or "").strip()
        if not target:
            return
        with self.lock:
            if self.last_active_ui_id == target:
                self.last_active_ui_id = None
            stale_keys = [
                key for key, value in self.last_active_ui_by_session.items() if value == target
            ]
            for key in stale_keys:
                self.last_active_ui_by_session.pop(key, None)

    def preferred(self, *, session_id: Optional[str]) -> Optional[str]:
        resolved_session_id = str(session_id or "").strip()
        with self.lock:
            if resolved_session_id:
                preferred = self.last_active_ui_by_session.get(resolved_session_id)
                if preferred:
                    return preferred
            return self.last_active_ui_id

    def reset(self) -> None:
        with self.lock:
            self.last_active_ui_id = None
            self.last_active_ui_by_session.clear()
