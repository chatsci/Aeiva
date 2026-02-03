"""
Raw Markdown memory (journal + neuron).

Stores dialogue sessions in daily Markdown files and keeps
long-term user memory in <username>.md under each user folder.
"""

from __future__ import annotations

import json
import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, tzinfo
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union
from uuid import uuid4

from aeiva.config.base_config import BaseConfig
from aeiva.neuron import BaseNeuron, NeuronConfig, Signal
from aeiva.event.event_names import EventNames

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _json_dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _coerce_text(content: Any) -> str:
    if isinstance(content, (dict, list)):
        return json.dumps(content, ensure_ascii=False, indent=2)
    return str(content)


def _indent_block(text: str, indent: str = "  ") -> str:
    lines = text.splitlines() or [""]
    return "\n".join(f"{indent}{line}" for line in lines)


def _from_signal_ts(signal: Signal) -> datetime:
    return datetime.fromtimestamp(signal.timestamp, tz=timezone.utc)


def _short_time(dt: datetime, tz: Optional[tzinfo] = None) -> str:
    """Format datetime as compact local-time string: 'YYYY-MM-DD HH:MM'."""
    local = dt.astimezone(tz) if tz else dt.astimezone()
    return local.strftime("%Y-%m-%d %H:%M")


def _iso_week(dt: datetime) -> Tuple[int, int]:
    iso = dt.isocalendar()
    return iso.year, iso.week


@dataclass
class RawMemoryConfig(BaseConfig):
    """
    Configuration for raw Markdown memory journal.
    """

    base_dir: str = "storage/memory"
    user_id: str = "User"
    ai_name: str = "Maid"
    user_memory_file: Optional[str] = None
    timezone: Optional[str] = None


@dataclass
class RawUtterance:
    role: str
    content: Any
    timestamp: datetime
    meta: Dict[str, Any] = field(default_factory=dict)
    files: List[str] = field(default_factory=list)


@dataclass
class RawSession:
    session_id: str
    start_time: datetime
    meta: Dict[str, Any] = field(default_factory=dict)
    utterances: List[RawUtterance] = field(default_factory=list)


class RawMemoryJournal:
    """
    Append-only raw memory journal in Markdown.

    Directory layout:
        storage/memory/<user_id>/
            <user_id>.md          # User long-term memory
            YY-MM-DD.md           # Daily memory (sessions)
            YY-MM.md              # Monthly summary
            YY.md                 # Yearly summary
            YY-WeekWW.md          # Weekly summary
    """

    def __init__(self, config: Optional[Union[RawMemoryConfig, Dict[str, Any]]] = None):
        if config is None:
            self.config = RawMemoryConfig()
        elif isinstance(config, dict):
            self.config = RawMemoryConfig(**config)
        else:
            self.config = config

        self._base_dir = self._resolve_dir(self.config.base_dir)
        self.user_id = self._safe_user_id(self.config.user_id)
        self._user_dir = self._base_dir / self.user_id
        self._sessions: Dict[str, RawSession] = {}
        self._tzinfo = self._resolve_timezone(self.config.timezone)

        user_memory_name = self.config.user_memory_file or f"{self.user_id}.md"
        self._user_memory_path = self._user_dir / user_memory_name

    # ---- session lifecycle ----

    def start_session(
        self,
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        sid = session_id or uuid4().hex
        start_time = start_time or _utc_now()
        if sid not in self._sessions:
            self._sessions[sid] = RawSession(
                session_id=sid,
                start_time=start_time,
                meta=meta or {},
            )
        return sid

    def append_utterance(
        self,
        session_id: str,
        role: str,
        content: Any,
        timestamp: Optional[datetime] = None,
        meta: Optional[Dict[str, Any]] = None,
        files: Optional[Sequence[str]] = None,
    ) -> None:
        timestamp = timestamp or _utc_now()
        if session_id not in self._sessions:
            self.start_session(session_id=session_id, start_time=timestamp)
        utterance = RawUtterance(
            role=role,
            content=content,
            timestamp=timestamp,
            meta=meta or {},
            files=list(files) if files else [],
        )
        self._sessions[session_id].utterances.append(utterance)

    def end_session(
        self,
        session_id: str,
        end_time: Optional[datetime] = None,
        summary: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        user_memory_updates: Optional[Sequence[str]] = None,
    ) -> Path:
        end_time = end_time or _utc_now()
        session = self._sessions.pop(session_id, None)
        if session is None:
            session = RawSession(session_id=session_id, start_time=end_time)

        content = self._format_session_block(session, end_time, summary, meta)
        daily_path = self._daily_path(end_time)
        if not self._session_block_exists(daily_path, session_id):
            self._append_to_file(daily_path, content, header=f"# {self._date_key(end_time)}\n\n")

        if user_memory_updates:
            self.append_user_memory(
                user_memory_updates,
                timestamp=end_time,
                session_id=session_id,
            )

        return daily_path

    def render_session(
        self,
        session_id: str,
        end_time: Optional[datetime] = None,
        summary: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        end_time = end_time or _utc_now()
        return self._format_session_block(session, end_time, summary, meta)

    # ---- summaries ----

    def append_period_summary(
        self,
        period: str,
        summary: str,
        summary_time: Optional[datetime] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Path:
        summary_time = summary_time or _utc_now()
        path = self._period_path(period, summary_time)
        header = f"# {self._period_title(period, summary_time)}\n\n"
        block = self._format_period_summary_block(period, summary, meta)
        self._append_to_file(path, block, header=header)
        return path

    def append_session_summary(
        self,
        session_id: str,
        summary: str,
        summary_time: Optional[datetime] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Path:
        summary_time = summary_time or _utc_now()
        path = self._daily_path(summary_time)
        header = f"# {self._date_key(summary_time)}\n\n"
        block = self._format_session_summary_block(session_id, summary, meta)
        self._append_to_file(path, block, header=header)
        return path

    def append_user_memory(
        self,
        updates: Sequence[str] | str,
        timestamp: Optional[datetime] = None,
        session_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Path:
        timestamp = timestamp or _utc_now()
        entries = [updates] if isinstance(updates, str) else list(updates)
        if not entries:
            return self._user_memory_path

        header = "# User Memory\n\n"
        lines = []
        for entry in entries:
            line = f"- [{timestamp.isoformat()}]"
            if session_id:
                line += f" (session={session_id})"
            line += f" {entry.strip()}\n"
            lines.append(line)

        self._append_to_file(self._user_memory_path, "".join(lines), header=header)
        return self._user_memory_path

    # ---- formatting ----

    def _format_session_block(
        self,
        session: RawSession,
        end_time: datetime,
        summary: Optional[str],
        end_meta: Optional[Dict[str, Any]],
    ) -> str:
        start_str = _short_time(session.start_time, self._tzinfo)
        end_str = _short_time(end_time, self._tzinfo)
        lines = [
            f"## Session {session.session_id}",
            f"{start_str} - {end_str}",
            "",
            "### Dialogue",
            "",
        ]

        for utterance in session.utterances:
            lines.append(self._format_utterance(utterance))

        if summary:
            lines.append("")
            lines.append("### Summary")
            lines.append(summary.strip())

        lines.append("")
        return "\n".join(lines) + "\n"

    def _format_utterance(self, utterance: RawUtterance) -> str:
        text = _coerce_text(utterance.content)
        name = self._role_name(utterance.role)
        time_str = _short_time(utterance.timestamp, self._tzinfo)
        if "\n" in text:
            return f"- {time_str}: {name}:\n{_indent_block(text, '  ')}"
        return f"- {time_str}: {name}: {text}"

    def _role_name(self, role: str) -> str:
        if role == "user":
            return self.config.user_id
        if role == "assistant":
            return self.config.ai_name
        return role

    @staticmethod
    def _format_summary_block(summary: str, meta: Optional[Dict[str, Any]]) -> str:
        block = summary.strip() + "\n"
        block += "\n"
        return block

    @classmethod
    def summary_heading(cls, period: str) -> str:
        period = period.lower()
        if period == "daily":
            return "### Daily Summary"
        if period == "weekly":
            return "### Weekly Summary"
        if period == "monthly":
            return "### Monthly Summary"
        if period == "yearly":
            return "### Yearly Summary"
        return "### Summary"

    @classmethod
    def _format_period_summary_block(
        cls,
        period: str,
        summary: str,
        meta: Optional[Dict[str, Any]],
    ) -> str:
        lines = [cls.summary_heading(period), "", summary.strip()]
        lines.append("")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _format_session_summary_block(
        session_id: str,
        summary: str,
        meta: Optional[Dict[str, Any]],
    ) -> str:
        lines = [f"### Session Summary {session_id}", "", summary.strip()]
        lines.append("")
        return "\n".join(lines) + "\n"

    # ---- paths ----

    @staticmethod
    def _safe_user_id(user_id: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", user_id or "")
        return safe or "user"

    @staticmethod
    def _resolve_dir(value: str) -> Path:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        return path

    def _date_key(self, dt: datetime) -> str:
        local = dt.astimezone(self._tzinfo) if self._tzinfo else dt.astimezone()
        return local.strftime("%y-%m-%d")

    def _month_key(self, dt: datetime) -> str:
        local = dt.astimezone(self._tzinfo) if self._tzinfo else dt.astimezone()
        return local.strftime("%y-%m")

    def _year_key(self, dt: datetime) -> str:
        local = dt.astimezone(self._tzinfo) if self._tzinfo else dt.astimezone()
        return local.strftime("%y")

    def _daily_path(self, dt: datetime) -> Path:
        return self._user_dir / f"{self._date_key(dt)}.md"

    def _period_path(self, period: str, dt: datetime) -> Path:
        period = period.lower()
        if period == "daily":
            return self._daily_path(dt)
        if period == "weekly":
            year, week = _iso_week(dt)
            return self._user_dir / f"{str(year)[-2:]}-Week{week:02d}.md"
        if period == "monthly":
            return self._user_dir / f"{self._month_key(dt)}.md"
        if period == "yearly":
            return self._user_dir / f"{self._year_key(dt)}.md"
        raise ValueError(f"Unknown summary period: {period}")

    def daily_path(self, dt: datetime) -> Path:
        return self._daily_path(dt)

    def period_path(self, period: str, dt: datetime) -> Path:
        return self._period_path(period, dt)

    def _period_title(self, period: str, dt: datetime) -> str:
        period = period.lower()
        if period == "daily":
            return self._date_key(dt)
        if period == "weekly":
            year, week = _iso_week(dt)
            return f"{str(year)[-2:]}-Week{week:02d}"
        if period == "monthly":
            return self._month_key(dt)
        if period == "yearly":
            return self._year_key(dt)
        return period

    def _append_to_file(self, path: Path, content: str, header: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(header, encoding="utf-8")
        with path.open("a", encoding="utf-8") as f:
            f.write(content)

    def _session_block_exists(self, path: Path, session_id: str) -> bool:
        if not path.exists():
            return False
        marker = f"## Session {session_id}"
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return False
        return marker in text

    @staticmethod
    def _resolve_timezone(value: Optional[str]) -> Optional[tzinfo]:
        if not value or str(value).lower() in {"local", "system"}:
            return datetime.now().astimezone().tzinfo

        text = str(value)
        if text.startswith(("+", "-")) and len(text) in {3, 5, 6}:
            sign = 1 if text[0] == "+" else -1
            parts = text[1:].split(":")
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            return timezone(sign * (hours * 3600 + minutes * 60))

        try:
            from zoneinfo import ZoneInfo
            return ZoneInfo(text)
        except Exception:
            logger.warning("Unknown timezone '%s', falling back to local.", value)
            return datetime.now().astimezone().tzinfo


# =========================
# Raw Memory Neuron
# =========================


DEFAULT_INPUT_EVENTS = [
    EventNames.PERCEPTION_OUTPUT,
    EventNames.COGNITION_THOUGHT,
    EventNames.RAW_MEMORY_SESSION_START,
    EventNames.RAW_MEMORY_SESSION_END,
    EventNames.RAW_MEMORY_UTTERANCE,
    EventNames.RAW_MEMORY_USER_UPDATE,
    EventNames.AGENT_STOP,
]


@dataclass
class RawMemoryNeuronConfig(NeuronConfig):
    raw_memory: RawMemoryConfig = field(default_factory=RawMemoryConfig)
    input_events: List[str] = field(default_factory=lambda: DEFAULT_INPUT_EVENTS.copy())
    output_event: str = EventNames.RAW_MEMORY_RESULT
    auto_start_session: bool = True
    auto_close_on_reply: bool = False


class RawMemoryNeuron(BaseNeuron):
    """
    Raw memory neuron: records dialogue turns into Markdown journal.
    """

    EMISSIONS = [
        EventNames.RAW_MEMORY_RESULT,
        EventNames.RAW_MEMORY_ERROR,
        EventNames.RAW_MEMORY_SESSION_CLOSED,
    ]
    CONFIG_CLASS = RawMemoryNeuronConfig

    def __init__(
        self,
        name: str = "raw_memory",
        config: Optional[Union[RawMemoryNeuronConfig, Dict[str, Any]]] = None,
        event_bus: Any = None,
        **kwargs,
    ):
        neuron_config = self.build_config(config)

        super().__init__(name=name, config=neuron_config, event_bus=event_bus, **kwargs)
        self.SUBSCRIPTIONS = self.config.input_events.copy()

        self._journals: Dict[str, RawMemoryJournal] = {}
        self._active_sessions: Dict[str, str] = {}
        self._assistant_buffers: Dict[str, List[str]] = {}
        self._events_processed = 0

    @classmethod
    def build_config(cls, data: Any) -> RawMemoryNeuronConfig:
        if isinstance(data, RawMemoryNeuronConfig):
            return data
        if not isinstance(data, dict):
            return RawMemoryNeuronConfig()
        raw_cfg = data.get("raw_memory", {}) if isinstance(data.get("raw_memory"), dict) else {}
        direct = {k: v for k, v in data.items() if k in RawMemoryConfig.__dataclass_fields__}
        raw_cfg = {**direct, **raw_cfg}
        raw_config = RawMemoryConfig(**raw_cfg)
        return RawMemoryNeuronConfig(
            raw_memory=raw_config,
            input_events=data.get("input_events", DEFAULT_INPUT_EVENTS.copy()),
            output_event=data.get("output_event", EventNames.RAW_MEMORY_RESULT),
            auto_start_session=data.get("auto_start_session", True),
            auto_close_on_reply=data.get("auto_close_on_reply", False),
        )

    async def process(self, signal: Signal) -> Optional[Dict[str, Any]]:
        self._events_processed += 1
        try:
            source = signal.source
            logger.info("RawMemoryNeuron processing event #%d source=%s", self._events_processed, source)
            if source == EventNames.RAW_MEMORY_SESSION_START:
                return self._handle_session_start(signal)
            if source == EventNames.RAW_MEMORY_SESSION_END:
                return await self._handle_session_end(signal)
            if source == EventNames.RAW_MEMORY_UTTERANCE:
                return self._handle_explicit_utterance(signal)
            if source == EventNames.RAW_MEMORY_USER_UPDATE:
                return self._handle_user_update(signal)
            if source == EventNames.AGENT_STOP:
                return await self._handle_agent_stop(signal)
            perception_prefix = EventNames.ALL_PERCEPTION[:-1]
            if source.startswith(perception_prefix) or source == perception_prefix[:-1]:
                result = self._handle_perception(signal)
                logger.info("RawMemoryNeuron recorded perception: %s", result)
                return result
            if source.startswith("cognition") and "query" not in source:
                result = self._handle_cognition_thought(signal)
                logger.info("RawMemoryNeuron recorded cognition: %s", result)
                return result
            logger.debug("RawMemoryNeuron ignoring unmatched source: %s", source)
        except Exception as exc:
            logger.error("RawMemoryNeuron error: %s", exc, exc_info=True)
            await self._emit_error(str(exc), signal)
            return {"success": False, "error": str(exc)}
        return None

    # ---- handlers ----

    def _handle_session_start(self, signal: Signal) -> Dict[str, Any]:
        payload = signal.data if isinstance(signal.data, dict) else {}
        user_id = self._extract_user_id(signal)
        session_id = payload.get("session_id") or uuid4().hex
        meta = payload.get("meta") or payload.get("metadata")
        start_time = self._extract_datetime(payload.get("start_time")) or _utc_now()
        journal = self._journal(user_id)
        journal.start_session(session_id=session_id, start_time=start_time, meta=meta)
        self._active_sessions[user_id] = session_id
        return {"success": True, "session_id": session_id, "user_id": user_id}

    async def _handle_session_end(self, signal: Signal) -> Dict[str, Any]:
        payload = signal.data if isinstance(signal.data, dict) else {}
        user_id = self._extract_user_id(signal)
        session_id = payload.get("session_id") or self._active_sessions.get(user_id)
        if not session_id:
            return {"success": False, "error": "No active session"}
        end_time = self._extract_datetime(payload.get("end_time")) or _utc_now()
        summary = payload.get("summary")
        meta = payload.get("meta") or payload.get("metadata")
        user_updates = payload.get("user_memory_updates")
        path = await self._end_session(
            signal=signal,
            user_id=user_id,
            session_id=session_id,
            end_time=end_time,
            summary=summary,
            meta=meta,
            user_updates=user_updates,
        )
        return {"success": True, "path": str(path), "session_id": session_id}

    async def _handle_agent_stop(self, signal: Signal) -> Dict[str, Any]:
        if not self._active_sessions:
            return {"success": True, "closed": 0}
        end_time = _utc_now()
        closed = 0
        for user_id, session_id in list(self._active_sessions.items()):
            await self._end_session(
                signal=signal,
                user_id=user_id,
                session_id=session_id,
                end_time=end_time,
                summary=None,
                meta={"trigger": EventNames.AGENT_STOP},
                user_updates=None,
            )
            closed += 1
        return {"success": True, "closed": closed}

    async def _end_session(
        self,
        signal: Signal,
        user_id: str,
        session_id: str,
        end_time: datetime,
        summary: Optional[str],
        meta: Optional[Dict[str, Any]],
        user_updates: Optional[Sequence[str]],
    ) -> Path:
        journal = self._journal(user_id)
        session = journal._sessions.get(session_id)
        if session is None or (not session.utterances and not summary and not user_updates):
            self._active_sessions.pop(user_id, None)
            self._assistant_buffers.pop(user_id, None)
            return journal.daily_path(end_time)

        session_text = journal.render_session(session_id=session_id, end_time=end_time)
        path = journal.end_session(
            session_id=session_id,
            end_time=end_time,
            summary=summary,
            meta=meta,
            user_memory_updates=user_updates,
        )
        self._active_sessions.pop(user_id, None)
        self._assistant_buffers.pop(user_id, None)
        await self._emit_session_closed(
            signal=signal,
            user_id=user_id,
            session_id=session_id,
            session=session,
            session_text=session_text,
            end_time=end_time,
            path=path,
        )
        return path

    def _handle_explicit_utterance(self, signal: Signal) -> Dict[str, Any]:
        payload = signal.data if isinstance(signal.data, dict) else {}
        user_id = self._extract_user_id(signal)
        session_id = payload.get("session_id") or self._ensure_session(user_id)
        role = payload.get("role", "user")
        content = payload.get("content")
        if content is None:
            return {"success": False, "error": "Missing content"}
        timestamp = self._extract_datetime(payload.get("timestamp")) or _utc_now()
        files = payload.get("files")
        meta = payload.get("meta") or payload.get("metadata")
        journal = self._journal(user_id)
        journal.append_utterance(
            session_id=session_id,
            role=role,
            content=content,
            timestamp=timestamp,
            meta=meta,
            files=files,
        )
        return {"success": True, "session_id": session_id, "role": role}

    def _handle_user_update(self, signal: Signal) -> Dict[str, Any]:
        payload = signal.data if isinstance(signal.data, dict) else {}
        user_id = self._extract_user_id(signal)
        updates = payload.get("updates") or payload.get("content")
        if not updates:
            return {"success": False, "error": "Missing updates"}
        timestamp = self._extract_datetime(payload.get("timestamp")) or _utc_now()
        session_id = payload.get("session_id")
        meta = payload.get("meta") or payload.get("metadata")
        journal = self._journal(user_id)
        path = journal.append_user_memory(
            updates=updates,
            timestamp=timestamp,
            session_id=session_id,
            meta=meta,
        )
        return {"success": True, "path": str(path)}

    async def _emit_session_closed(
        self,
        signal: Signal,
        user_id: str,
        session_id: str,
        session: Optional[RawSession],
        session_text: Optional[str],
        end_time: datetime,
        path: Path,
    ) -> None:
        if not self.events:
            return
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "session_id": session_id,
            "end_time": end_time,
            "path": str(path),
        }
        if session:
            payload["start_time"] = session.start_time
            payload["utterance_count"] = len(session.utterances)
        if session_text:
            payload["session_text"] = session_text
        await self.events.emit(EventNames.RAW_MEMORY_SESSION_CLOSED, payload=payload)

    async def _emit_session_started(
        self,
        user_id: str,
        session_id: str,
        start_time: datetime,
    ) -> None:
        if not self.events:
            return
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "session_id": session_id,
            "start_time": start_time,
        }
        await self.events.emit(EventNames.RAW_MEMORY_SESSION_START, payload=payload)

    def _schedule_session_start(
        self,
        user_id: str,
        session_id: str,
        start_time: datetime,
    ) -> None:
        if not self.events:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self._emit_session_started(user_id, session_id, start_time))

    def _handle_perception(self, signal: Signal) -> Dict[str, Any]:
        user_id = self._extract_user_id(signal)
        session_id = self._ensure_session(user_id)
        content, meta, files = self._extract_perception_content(signal)
        if content is None:
            return {"success": False, "error": "No perception content"}
        journal = self._journal(user_id)
        journal.append_utterance(
            session_id=session_id,
            role="user",
            content=content,
            timestamp=_from_signal_ts(signal),
            meta=meta,
            files=files,
        )
        return {"success": True, "session_id": session_id, "role": "user"}

    def _handle_cognition_thought(self, signal: Signal) -> Dict[str, Any]:
        user_id = self._extract_user_id(signal)
        session_id = self._ensure_session(user_id)
        thought, streaming, final = self._extract_cognition_thought(signal)
        if thought is None and not (streaming and final):
            return {"success": False, "error": "No cognition content"}
        if thought is None:
            thought = ""

        if streaming:
            buffer = self._assistant_buffers.setdefault(user_id, [])
            if thought:
                buffer.append(thought)
            if not final:
                return {"success": True, "streaming": True}
            thought = "".join(buffer)
            self._assistant_buffers[user_id] = []

        journal = self._journal(user_id)
        journal.append_utterance(
            session_id=session_id,
            role="assistant",
            content=thought,
            timestamp=_from_signal_ts(signal),
            meta={},
        )

        if self.config.auto_close_on_reply and final:
            journal.end_session(session_id=session_id, end_time=_from_signal_ts(signal))
            self._active_sessions.pop(user_id, None)
            self._assistant_buffers.pop(user_id, None)

        return {"success": True, "session_id": session_id, "role": "assistant"}

    # ---- helpers ----

    def _journal(self, user_id: str) -> RawMemoryJournal:
        user_key = RawMemoryJournal._safe_user_id(user_id)
        if user_key not in self._journals:
            cfg = RawMemoryConfig(
                base_dir=self.config.raw_memory.base_dir,
                user_id=user_key,
                ai_name=self.config.raw_memory.ai_name,
                user_memory_file=self.config.raw_memory.user_memory_file,
                timezone=self.config.raw_memory.timezone,
            )
            self._journals[user_key] = RawMemoryJournal(cfg)
        return self._journals[user_key]


    def _ensure_session(self, user_id: str) -> str:
        session_id = self._active_sessions.get(user_id)
        if session_id:
            return session_id
        if not self.config.auto_start_session:
            return ""
        session_id = uuid4().hex
        start_time = _utc_now()
        journal = self._journal(user_id)
        journal.start_session(session_id=session_id, start_time=start_time)
        self._active_sessions[user_id] = session_id
        self._schedule_session_start(user_id, session_id, start_time)
        return session_id

    def _extract_user_id(self, signal: Signal) -> str:
        if isinstance(signal.data, dict):
            for key in ("user_id", "username", "user"):
                if key in signal.data:
                    return str(signal.data[key])
            meta = signal.data.get("meta") or signal.data.get("metadata")
            if isinstance(meta, dict):
                for key in ("user_id", "username", "user"):
                    if key in meta:
                        return str(meta[key])
        data = signal.data
        if hasattr(data, "metadata") and isinstance(data.metadata, dict):
            for key in ("user_id", "username", "user"):
                if key in data.metadata:
                    return str(data.metadata[key])
        return self.config.raw_memory.user_id

    def _extract_perception_content(self, signal: Signal) -> Tuple[Any, Dict[str, Any], List[str]]:
        data = signal.data
        # Handle Stimuli objects: dig into signals for the actual user content
        if hasattr(data, "signals") and data.signals:
            first = data.signals[0]
            inner = getattr(first, "data", None)
            meta = getattr(data, "metadata", None) or {}
            if isinstance(inner, dict):
                text = inner.get("text", inner.get("content", inner.get("data")))
                files = inner.get("files") or []
                return text or inner, meta, list(files)
            if inner is not None:
                return inner, meta, []
        if isinstance(data, dict):
            content = data.get("data", data.get("content", data))
            meta = data.get("meta") or data.get("metadata") or {}
            files = data.get("files") or []
            return content, meta, list(files) if files else []
        return data, {}, []

    def _extract_cognition_thought(self, signal: Signal) -> Tuple[Optional[str], bool, bool]:
        data = signal.data
        if isinstance(data, dict):
            # Use 'in' check instead of 'or' chain to preserve empty strings
            thought = None
            for key in ("thought", "output", "content"):
                if key in data:
                    thought = data[key]
                    break
            streaming = bool(data.get("streaming", False))
            final = bool(data.get("final", True))
            return thought, streaming, final
        if isinstance(data, str):
            return data, False, True
        return None, False, True

    @staticmethod
    def _extract_datetime(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    async def _emit_error(self, error: str, original_signal: Signal) -> None:
        if not self.events:
            return
        await self.events.emit(
            EventNames.RAW_MEMORY_ERROR,
            payload={
                "error": error,
                "source": original_signal.source,
                "trace_id": original_signal.trace_id,
            },
        )

    async def teardown(self) -> None:
        self._close_all_sessions()
        await super().teardown()

    def _close_all_sessions(self) -> None:
        if not self._active_sessions:
            return
        end_time = _utc_now()
        for user_id, session_id in list(self._active_sessions.items()):
            journal = self._journal(user_id)
            try:
                journal.end_session(session_id=session_id, end_time=end_time)
            except Exception as exc:
                logger.warning("Failed to close session %s: %s", session_id, exc)
        self._active_sessions.clear()
        self._assistant_buffers.clear()
