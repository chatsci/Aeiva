"""Session lifecycle manager for browser runtimes."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .runtime_common import BrowserRuntime, _parse_int_env


def _default_runtime_factory(profile: str, headless: bool) -> BrowserRuntime:
    # Lazy import avoids circular imports while keeping startup overhead low.
    from .browser_runtime import PlaywrightRuntime

    return PlaywrightRuntime(profile=profile, headless=headless)


@dataclass
class BrowserSession:
    profile: str
    headless: bool
    runtime: BrowserRuntime
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)


class BrowserSessionManager:
    """
    Profile-scoped browser runtime manager.

    Each profile has one persistent runtime guarded by a per-profile lock.
    """

    def __init__(
        self,
        runtime_factory: Optional[Callable[[str, bool], BrowserRuntime]] = None,
        *,
        max_sessions: Optional[int] = None,
        idle_ttl_seconds: Optional[int] = None,
    ) -> None:
        self._runtime_factory = runtime_factory or _default_runtime_factory
        self._sessions: Dict[str, BrowserSession] = {}
        self._manager_lock = asyncio.Lock()
        self._max_sessions = self._normalize_positive_int(
            max_sessions,
            fallback=_parse_int_env("AEIVA_BROWSER_MAX_SESSIONS", 8, 1),
            minimum=1,
        )
        self._idle_ttl_seconds = self._normalize_positive_int(
            idle_ttl_seconds,
            fallback=_parse_int_env("AEIVA_BROWSER_SESSION_IDLE_SECS", 1200, 60),
            minimum=60,
        )

    @staticmethod
    def _normalize_positive_int(value: Optional[int], *, fallback: int, minimum: int) -> int:
        if value is None:
            return max(minimum, int(fallback))
        try:
            parsed = int(value)
        except Exception:
            return max(minimum, int(fallback))
        return max(minimum, parsed)

    async def get_session(self, profile: str) -> Optional[BrowserSession]:
        async with self._manager_lock:
            return self._sessions.get(profile)

    async def ensure_session(self, profile: str, headless: bool) -> BrowserSession:
        clean_profile = profile.strip() or "default"
        await self._prune_sessions(exclude_profiles={clean_profile})
        session_to_stop: Optional[BrowserSession] = None
        async with self._manager_lock:
            current = self._sessions.get(clean_profile)
            if current and current.headless == bool(headless):
                current.last_used_at = time.time()
                return current

            if current is not None:
                self._sessions.pop(clean_profile, None)
                session_to_stop = current

        if session_to_stop is not None:
            async with session_to_stop.lock:
                await session_to_stop.runtime.stop()

        runtime = self._runtime_factory(clean_profile, bool(headless))
        session = BrowserSession(
            profile=clean_profile,
            headless=bool(headless),
            runtime=runtime,
        )
        try:
            await runtime.start()
        except Exception:
            # Ensure partially initialized runtimes do not leak processes/resources.
            try:
                await runtime.stop()
            except Exception:
                pass
            raise

        async with self._manager_lock:
            existing = self._sessions.get(clean_profile)
            if existing is not None:
                async with existing.lock:
                    await existing.runtime.stop()
            self._sessions[clean_profile] = session
        await self._prune_sessions(exclude_profiles={clean_profile})
        return session

    async def _prune_sessions(self, *, exclude_profiles: Optional[set[str]] = None) -> None:
        excluded = {str(item).strip() for item in (exclude_profiles or set()) if str(item).strip()}
        now = time.time()
        to_stop: List[BrowserSession] = []

        async with self._manager_lock:
            for profile, session in list(self._sessions.items()):
                if profile in excluded:
                    continue
                if session.lock.locked():
                    continue
                if now - float(session.last_used_at) >= float(self._idle_ttl_seconds):
                    popped = self._sessions.pop(profile, None)
                    if popped is not None:
                        to_stop.append(popped)

            overflow = len(self._sessions) - int(self._max_sessions)
            if overflow > 0:
                candidates = [
                    (profile, session)
                    for profile, session in self._sessions.items()
                    if profile not in excluded and not session.lock.locked()
                ]
                candidates.sort(key=lambda item: float(item[1].last_used_at))
                for profile, _ in candidates[:overflow]:
                    popped = self._sessions.pop(profile, None)
                    if popped is not None:
                        to_stop.append(popped)

        for session in to_stop:
            async with session.lock:
                await session.runtime.stop()

    async def run_with_session(
        self,
        *,
        profile: str,
        headless: bool,
        create: bool,
        fn: Callable[[BrowserRuntime], Any],
    ) -> Any:
        session: Optional[BrowserSession]
        if create:
            session = await self.ensure_session(profile, headless)
        else:
            session = await self.get_session(profile)
            if session is None:
                raise ValueError(f"Browser profile not running: {profile}")

        async with session.lock:
            session.last_used_at = time.time()
            return await fn(session.runtime)

    async def stop_session(self, profile: str) -> bool:
        clean_profile = profile.strip() or "default"
        async with self._manager_lock:
            session = self._sessions.pop(clean_profile, None)
        if session is None:
            return False
        async with session.lock:
            await session.runtime.stop()
        return True

    async def stop_all(self) -> None:
        async with self._manager_lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            async with session.lock:
                await session.runtime.stop()

    async def list_profiles(self) -> List[Dict[str, Any]]:
        async with self._manager_lock:
            items = list(self._sessions.values())

        profiles: List[Dict[str, Any]] = []
        for session in items:
            runtime_status = await session.runtime.status()
            profiles.append(
                {
                    "profile": session.profile,
                    "headless": session.headless,
                    "created_at": session.created_at,
                    "last_used_at": session.last_used_at,
                    "status": runtime_status,
                }
            )
        return profiles
