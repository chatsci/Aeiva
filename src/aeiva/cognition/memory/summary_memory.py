"""
SummaryMemoryNeuron: LLM-based summarization for raw memory.

Primary mechanism: **startup catchup** — on every program start, scan recent
daily files for unsummarized sessions and missing period summaries, then
generate them via LLM.  This eliminates all shutdown-timing dependencies.

The event-based path (raw_memory.session.closed) is kept as a best-effort
bonus for immediate feedback when the shutdown is clean.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from aeiva.neuron import BaseNeuron, NeuronConfig, Signal
from aeiva.cognition.memory.raw_memory import RawMemoryConfig, RawMemoryJournal
from aeiva.event.event_names import EventNames
from aeiva.llm.llm_client import LLMClient
from aeiva.llm.llm_gateway_config import LLMGatewayConfig

logger = logging.getLogger(__name__)

DEFAULT_INPUT_EVENTS = [
    EventNames.RAW_MEMORY_SESSION_START,
    EventNames.RAW_MEMORY_SESSION_CLOSED,
    EventNames.RAW_MEMORY_SUMMARY_REQUEST,
]
DEFAULT_SUMMARY_PERIODS = ["dialogue", "daily", "weekly", "monthly", "yearly"]

DEFAULT_SYSTEM_PROMPT = (
    "You are a memory summarizer for an AI assistant. "
    "Read the provided context and decide if a summary is worth saving. "
    "Return ONLY a JSON object with keys: "
    "\"summary\" (string, empty if skip) and \"user_memory_updates\" "
    "(array of strings with stable long-term facts about the user, optional). "
    "If nothing important, return {\"summary\": \"\", \"user_memory_updates\": []}. "
    "Do not include markdown, code fences, or extra commentary."
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SummaryMemoryNeuronConfig(NeuronConfig):
    raw_memory: RawMemoryConfig = field(default_factory=RawMemoryConfig)
    llm_gateway_config: Dict[str, Any] = field(default_factory=dict)
    input_events: List[str] = field(default_factory=lambda: DEFAULT_INPUT_EVENTS.copy())
    summary_periods: List[str] = field(default_factory=lambda: DEFAULT_SUMMARY_PERIODS.copy())
    startup_catchup_enabled: bool = True
    summary_temperature: float = 0.2
    summary_max_chars: int = 8000
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


class SummaryMemoryNeuron(BaseNeuron):
    """
    Summarize raw memory via LLM.

    Two mechanisms:
    1. **startup_catchup()** — scan files on startup, fill gaps (primary).
    2. **process()** — handle raw_memory.session.closed events (best-effort).
    """

    EMISSIONS = [EventNames.SUMMARY_MEMORY_RESULT]
    CONFIG_CLASS = SummaryMemoryNeuronConfig

    def __init__(
        self,
        name: str = "summary_memory",
        config: Optional[Union[SummaryMemoryNeuronConfig, Dict[str, Any]]] = None,
        event_bus: Any = None,
        **kwargs,
    ):
        neuron_config = self.build_config(config)

        super().__init__(name=name, config=neuron_config, event_bus=event_bus, **kwargs)
        self.SUBSCRIPTIONS = self.config.input_events.copy()
        self._base_dir = RawMemoryJournal._resolve_dir(self.config.raw_memory.base_dir)
        self._tzinfo = RawMemoryJournal._resolve_timezone(self.config.raw_memory.timezone)
        self._llm_client: Optional[LLMClient] = None
        self._enabled = True
        self._last_session_end: Dict[str, datetime] = {}

    @classmethod
    def build_config(cls, data: Any) -> SummaryMemoryNeuronConfig:
        if isinstance(data, SummaryMemoryNeuronConfig):
            return data
        if not isinstance(data, dict):
            return SummaryMemoryNeuronConfig()
        raw_cfg = data.get("raw_memory", {}) if isinstance(data.get("raw_memory"), dict) else {}
        raw_cfg = {k: v for k, v in raw_cfg.items() if k in RawMemoryConfig.__dataclass_fields__}
        direct = {k: v for k, v in data.items() if k in RawMemoryConfig.__dataclass_fields__}
        raw_cfg = {**direct, **raw_cfg}
        return SummaryMemoryNeuronConfig(
            raw_memory=RawMemoryConfig(**raw_cfg),
            llm_gateway_config=data.get("llm_gateway_config", {}),
            input_events=data.get("input_events", DEFAULT_INPUT_EVENTS.copy()),
            summary_periods=data.get("summary_periods", DEFAULT_SUMMARY_PERIODS.copy()),
            startup_catchup_enabled=bool(data.get("startup_catchup_enabled", True)),
            summary_temperature=data.get("summary_temperature", 0.2),
            summary_max_chars=data.get("summary_max_chars", 8000),
            system_prompt=data.get("system_prompt", DEFAULT_SYSTEM_PROMPT),
        )

    async def setup(self) -> None:
        await super().setup()
        try:
            self._llm_client = self._build_llm_client(self.config.llm_gateway_config)
        except Exception as exc:
            logger.warning("SummaryMemoryNeuron disabled (LLM init failed): %s", exc)
            self._enabled = False
            self._llm_client = None

    # ================================================================
    # Startup catchup — the primary summarization mechanism
    # ================================================================

    async def startup_catchup(self) -> Dict[str, Any]:
        """
        Catch up on missed summaries from previous runs.

        Called once at agent startup.  Scans recent daily files for
        unsummarized sessions and missing period summaries, then generates
        them via LLM.
        """
        if not self.config.startup_catchup_enabled:
            logger.info("SummaryMemoryNeuron startup catchup disabled by config")
            return {"skipped": True, "reason": "disabled_by_config"}

        if not self._enabled:
            logger.info("SummaryMemoryNeuron disabled, skipping startup catchup")
            return {"skipped": True, "reason": "llm_unavailable"}

        user_id = self.config.raw_memory.user_id
        results = {"dialogue_summaries": 0, "period_summaries": 0, "user_updates": 0}

        # 1. Summarize unsummarized dialogue sessions
        for sid, block, ts in self._find_unsummarized_sessions(user_id):
            context = self._strip_summary_sections(block)
            context = self._normalize_context(context)
            if not context:
                continue
            logger.info("Startup: summarizing session %s...", sid[:8])
            summary, updates = await self._summarize("dialogue", context, {"session_id": sid}, ts)
            if summary:
                self._write_dialogue_summary(user_id, sid, summary, ts, None)
                results["dialogue_summaries"] += 1
            elif self._should_write_empty_summary(context):
                self._write_dialogue_summary(user_id, sid, "", ts, {"skipped": True})
                results["dialogue_summaries"] += 1
            if updates:
                self._write_user_updates(user_id, updates, ts, sid, None)
                results["user_updates"] += len(updates)

        # 2. Fill missing period summaries for recent complete periods
        periods = [p.lower() for p in self.config.summary_periods]
        for period, ts in self._find_missing_period_summaries(user_id, periods):
            logger.info("Startup: generating %s summary...", period)
            await self._summarize_period(user_id, period, ts, {})
            results["period_summaries"] += 1

        logger.info("Startup catchup complete: %s", results)
        return results

    def _find_unsummarized_sessions(self, user_id: str) -> List[Tuple[str, str, datetime]]:
        """Find sessions in recent daily files that lack a summary."""
        user_dir = self._user_dir(user_id)
        if not user_dir.exists():
            return []

        results = []
        # Check last 7 daily files
        for path in sorted(user_dir.glob("??-??-??.md"), reverse=True)[:7]:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for sid in re.findall(r"^## Session (\w+)", text, re.MULTILINE):
                if f"### Session Summary {sid}" not in text:
                    block = self._extract_session_block(text, sid)
                    if block.strip():
                        parsed = self._parse_daily_filename(path.name)
                        ts = self._date_to_timestamp(parsed) if parsed else _utc_now()
                        results.append((sid, block, ts))
        return results

    def _find_latest_unsummarized_session(
        self, user_id: str,
    ) -> Optional[Tuple[str, str, datetime]]:
        """Return the most recent unsummarized session (or None)."""
        user_dir = self._user_dir(user_id)
        if not user_dir.exists():
            return None

        for path in sorted(user_dir.glob("??-??-??.md"), reverse=True)[:7]:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            sessions = re.findall(r"^## Session (\w+)", text, re.MULTILINE)
            if not sessions:
                continue
            missing = [sid for sid in sessions if f"### Session Summary {sid}" not in text]
            if not missing:
                continue
            sid = missing[-1]
            block = self._extract_session_block(text, sid)
            if not block.strip():
                continue
            parsed = self._parse_daily_filename(path.name)
            ts = self._date_to_timestamp(parsed) if parsed else _utc_now()
            return sid, block, ts
        return None

    def _find_missing_period_summaries(
        self, user_id: str, periods: List[str],
    ) -> List[Tuple[str, datetime]]:
        """Find recent complete periods that lack a summary file/section."""
        now = _utc_now()
        missing = []
        for period in ("daily", "weekly", "monthly", "yearly"):
            if period not in periods:
                continue
            ts = self._previous_period_time(period, now)
            if ts is None:
                continue
            journal = self._journal(user_id)
            # Check if there is any source data for this period
            if period == "daily":
                src = journal.daily_path(ts)
                if not src.exists():
                    continue
            else:
                paths = self._paths_for_period(user_id, period, ts)
                if not paths:
                    continue
            # Check if summary already exists
            dest = journal.period_path(period, ts) if period != "daily" else src
            if dest.exists():
                try:
                    content = dest.read_text(encoding="utf-8")
                except OSError:
                    content = ""
                heading = RawMemoryJournal.summary_heading(period)
                if heading in content:
                    continue
            missing.append((period, ts))
        return missing

    def _previous_period_time(self, period: str, now: datetime) -> Optional[datetime]:
        """Return a representative timestamp for the most recent *completed* period."""
        local = now.astimezone(self._tzinfo) if self._tzinfo else now.astimezone()
        if period == "daily":
            yesterday = local - timedelta(days=1)
            return yesterday.replace(hour=12, minute=0, second=0, microsecond=0)
        if period == "weekly":
            start_of_week = local - timedelta(days=local.weekday())
            last_week = start_of_week - timedelta(days=1)
            return last_week.replace(hour=12, minute=0, second=0, microsecond=0)
        if period == "monthly":
            first = local.replace(day=1)
            last_month = first - timedelta(days=1)
            return last_month.replace(hour=12, minute=0, second=0, microsecond=0)
        if period == "yearly":
            first = local.replace(month=1, day=1)
            last_year = first - timedelta(days=1)
            return last_year.replace(hour=12, minute=0, second=0, microsecond=0)
        return None

    # ================================================================
    # Event-based processing (best-effort, not critical)
    # ================================================================

    async def process(self, signal: Signal) -> Optional[Dict[str, Any]]:
        if not self._enabled:
            return {"success": False, "error": "LLM disabled"}

        try:
            if signal.source == EventNames.RAW_MEMORY_SESSION_START:
                return await self._handle_session_start(signal)
            if signal.source == EventNames.RAW_MEMORY_SESSION_CLOSED:
                return await self._handle_session_closed(signal)
            if signal.source == EventNames.RAW_MEMORY_SUMMARY_REQUEST:
                return await self._handle_summary_request(signal)
            return None
        except Exception as exc:
            logger.error("SummaryMemoryNeuron error: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}

    async def _handle_session_start(self, signal: Signal) -> Dict[str, Any]:
        payload = signal.data if isinstance(signal.data, dict) else {}
        user_id = self._extract_user_id(signal)
        results: Dict[str, Any] = {"dialogue": False, "periods": [], "user_updates": 0}

        # Dialogue summary for the most recent unsummarized session
        latest = self._find_latest_unsummarized_session(user_id)
        if latest and "dialogue" in [p.lower() for p in self.config.summary_periods]:
            sid, block, ts = latest
            if not await self._summary_exists(user_id, "dialogue", ts, sid):
                context = self._strip_summary_sections(block)
                context = self._normalize_context(context)
                if context:
                    summary, updates = await self._summarize(
                        "dialogue", context, {"session_id": sid}, ts,
                    )
                    if summary:
                        self._write_dialogue_summary(user_id, sid, summary, ts, payload.get("meta"))
                        results["dialogue"] = True
                    elif self._should_write_empty_summary(context):
                        self._write_dialogue_summary(user_id, sid, "", ts, {"skipped": True})
                        results["dialogue"] = True
                    if updates:
                        self._write_user_updates(user_id, updates, ts, sid, payload.get("meta"))
                        results["user_updates"] += len(updates)

        # Missing period summaries for the most recent completed periods
        periods = [p.lower() for p in self.config.summary_periods]
        for period, ts in self._find_missing_period_summaries(user_id, periods):
            await self._summarize_period(user_id, period, ts, payload)
            results["periods"].append(period)

        return {"success": True, "results": results}

    async def _handle_session_closed(self, signal: Signal) -> Dict[str, Any]:
        payload = signal.data if isinstance(signal.data, dict) else {}
        user_id = self._extract_user_id(signal)
        session_id = payload.get("session_id")
        end_time = self._extract_datetime(payload.get("end_time")) or self._from_signal_ts(signal)
        session_text = payload.get("session_text") or payload.get("session_block")

        summary_periods = [p.lower() for p in self.config.summary_periods]
        results: Dict[str, Any] = {"dialogue": False}

        if "dialogue" in summary_periods and session_id and session_text:
            if not await self._summary_exists(user_id, "dialogue", end_time, session_id):
                context = self._strip_summary_sections(session_text)
                context = self._normalize_context(context)
                if context:
                    summary, user_updates = await self._summarize(
                        "dialogue", context, payload, end_time,
                    )
                    if summary:
                        self._write_dialogue_summary(user_id, session_id, summary, end_time, payload.get("meta"))
                        results["dialogue"] = True
                    elif self._should_write_empty_summary(context):
                        self._write_dialogue_summary(
                            user_id,
                            session_id,
                            "",
                            end_time,
                            {"skipped": True},
                        )
                        results["dialogue"] = True
                    if user_updates:
                        self._write_user_updates(user_id, user_updates, end_time, session_id, payload.get("meta"))

        # Period crossing detection
        prev_end = self._last_session_end.get(user_id)
        self._last_session_end[user_id] = end_time
        if prev_end:
            for period in ("daily", "weekly", "monthly", "yearly"):
                if period not in summary_periods:
                    continue
                if self._period_key(period, prev_end) != self._period_key(period, end_time):
                    await self._summarize_period(user_id, period, prev_end, payload)

        return {"success": True, "results": results}

    async def _handle_summary_request(self, signal: Signal) -> Dict[str, Any]:
        payload = signal.data if isinstance(signal.data, dict) else {}
        period = str(payload.get("period", "dialogue")).lower()
        if period not in self.config.summary_periods:
            return {"success": True, "skipped": True, "reason": "period_disabled"}

        user_id = self._extract_user_id(signal)
        timestamp = self._extract_datetime(payload.get("timestamp")) or self._from_signal_ts(signal)
        session_id = payload.get("session_id")
        context = payload.get("context")

        if await self._summary_exists(user_id, period, timestamp, session_id):
            return {"success": True, "skipped": True, "reason": "already_summarized"}

        if not context:
            context = await self._load_period_context(user_id, period, timestamp, session_id)
        context = self._normalize_context(context)
        if not context:
            return {"success": True, "skipped": True, "reason": "empty_context"}

        summary, user_updates = await self._summarize(period, context, payload, timestamp)
        if summary:
            self._write_summary(user_id, period, summary, timestamp, session_id, payload.get("meta"))
        elif self._should_write_empty_summary(context):
            self._write_summary(user_id, period, "", timestamp, session_id, {"skipped": True})
        if user_updates:
            self._write_user_updates(user_id, user_updates, timestamp, session_id, payload.get("meta"))

        return {"success": True, "summary_emitted": bool(summary), "user_updates": len(user_updates)}

    # ================================================================
    # LLM interaction
    # ================================================================

    def _build_llm_client(self, cfg: Dict[str, Any]) -> LLMClient:
        llm_api_key = cfg.get("llm_api_key")
        valid_keys = LLMGatewayConfig.__dataclass_fields__.keys()
        params = {k: v for k, v in cfg.items() if k in valid_keys}
        params["llm_api_key"] = llm_api_key
        params["llm_temperature"] = self.config.summary_temperature
        params["llm_use_async"] = True
        params["llm_stream"] = False
        return LLMClient(LLMGatewayConfig(**params))

    async def _summarize(
        self, period: str, context: str, payload: Dict[str, Any], timestamp: datetime,
    ) -> Tuple[str, List[str]]:
        if not self._llm_client:
            if self._count_utterances(context) >= 2:
                return self._fallback_summary(context), []
            return "", []
        messages = self._build_messages(period, context, payload, timestamp)
        logger.info("Calling LLM for %s summary (%d chars context)", period, len(context))
        try:
            response = await self._llm_client.agenerate(messages)
            summary, user_updates = self._parse_llm_response(response)
            if not summary and self._count_utterances(context) >= 2:
                summary = self._fallback_summary(context)
            return summary, user_updates
        except Exception as exc:
            logger.warning("Summary LLM failed, using fallback: %s", exc)
            return self._fallback_summary(context), []

    def _build_messages(
        self, period: str, context: str, payload: Dict[str, Any], timestamp: datetime,
    ) -> List[Dict[str, str]]:
        session_id = payload.get("session_id")
        time_str = self._local_time(timestamp)
        header = f"Period: {period}\nTime: {time_str}"
        if session_id:
            header += f"\nSession: {session_id}"
        return [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": f"{header}\n\nContext:\n{context}"},
        ]

    def _parse_llm_response(self, response: str) -> Tuple[str, List[str]]:
        if not response:
            return "", []
        text = response.strip()
        try:
            data = json.loads(text)
            summary = str(data.get("summary", "") or "").strip()
            updates = data.get("user_memory_updates") or []
            if isinstance(updates, str):
                updates = [updates]
            updates = [str(item).strip() for item in updates if str(item).strip()]
        except json.JSONDecodeError:
            summary = text
            updates = []
        if summary.lower() in {"skip", "none", "null"}:
            summary = ""
        return summary, updates

    def _normalize_context(self, context: Optional[str]) -> str:
        if not context:
            return ""
        text = context.strip()
        if not text:
            return ""
        max_chars = self.config.summary_max_chars
        if max_chars and len(text) > max_chars:
            half = max_chars // 2
            text = f"{text[:half].strip()}\n...\n{text[-half:].strip()}"
        return text

    @staticmethod
    def _fallback_summary(context: str) -> str:
        lines = [l.strip() for l in context.splitlines() if l.strip().startswith("- ")]
        if not lines:
            return ""
        turns = len(lines)
        preview = lines[:2]
        tail = lines[-1:] if turns > 2 else []
        bullets = preview + (["..."] if turns > 3 else []) + tail
        return f"{turns}-turn exchange.\n" + "\n".join(bullets)

    @staticmethod
    def _count_utterances(context: str) -> int:
        return sum(1 for l in context.splitlines() if l.strip().startswith("- "))

    def _should_write_empty_summary(self, context: str) -> bool:
        return self._count_utterances(context) > 0

    # ================================================================
    # Summary existence checks and file I/O
    # ================================================================

    async def _summary_exists(
        self, user_id: str, period: str, timestamp: datetime, session_id: Optional[str],
    ) -> bool:
        path = await self._summary_path(user_id, period, timestamp)
        if not path or not path.exists():
            return False
        text = await self._read_file(path)
        if period == "dialogue" and session_id:
            return f"### Session Summary {session_id}" in text
        return RawMemoryJournal.summary_heading(period) in text

    async def _summary_path(self, user_id: str, period: str, timestamp: datetime) -> Optional[Path]:
        journal = self._journal(user_id)
        return journal.daily_path(timestamp) if period == "dialogue" else journal.period_path(period, timestamp)

    async def _load_period_context(
        self, user_id: str, period: str, timestamp: datetime, session_id: Optional[str],
    ) -> str:
        if period == "dialogue" and session_id:
            journal = self._journal(user_id)
            path = journal.daily_path(timestamp)
            if not path.exists():
                return ""
            text = await self._read_file(path)
            block = self._extract_session_block(text, session_id)
            return self._strip_summary_sections(block)

        period = period.lower()
        if period == "daily":
            paths = self._paths_for_period(user_id, period, timestamp)
            if not paths:
                return ""
            texts = []
            for path in paths:
                text = await self._read_file(path)
                text = self._strip_summary_sections(text)
                if text.strip():
                    texts.append(text)
            return "\n\n".join(texts)

        lower_period = {
            "weekly": "daily",
            "monthly": "weekly",
            "yearly": "monthly",
        }.get(period)
        if not lower_period:
            return ""
        paths = self._summary_paths_for_period(user_id, period, timestamp)
        if not paths:
            return ""
        heading = RawMemoryJournal.summary_heading(lower_period)
        summaries: List[str] = []
        for path in paths:
            text = await self._read_file(path)
            blocks = self._extract_summary_blocks(text, heading)
            summaries.extend([b for b in blocks if b.strip()])
        return "\n\n".join(summaries).strip()

    async def _summarize_period(
        self, user_id: str, period: str, timestamp: datetime, payload: Dict[str, Any],
    ) -> None:
        if await self._summary_exists(user_id, period, timestamp, None):
            return
        context = await self._load_period_context(user_id, period, timestamp, None)
        context = self._normalize_context(context)
        if not context:
            return
        summary, user_updates = await self._summarize(period, context, payload, timestamp)
        if summary:
            self._write_summary(user_id, period, summary, timestamp, None, payload.get("meta"))
        elif self._should_write_empty_summary(context):
            self._write_summary(user_id, period, "", timestamp, None, {"skipped": True})
        if user_updates:
            self._write_user_updates(user_id, user_updates, timestamp, None, payload.get("meta"))

    def _paths_for_period(self, user_id: str, period: str, timestamp: datetime) -> List[Path]:
        journal = self._journal(user_id)
        if period == "daily":
            path = journal.daily_path(timestamp)
            return [path] if path.exists() else []
        target_key = self._period_key(period, timestamp)
        user_dir = self._user_dir(user_id)
        if not user_dir.exists():
            return []
        paths = []
        for path in sorted(user_dir.glob("??-??-??.md")):
            parsed = self._parse_daily_filename(path.name)
            if parsed and self._period_key_from_date(period, parsed) == target_key:
                paths.append(path)
        return paths

    def _summary_paths_for_period(self, user_id: str, period: str, timestamp: datetime) -> List[Path]:
        """Return the lower-level summary file paths used to build the target period."""
        period = period.lower()
        if period == "weekly":
            return self._paths_for_period(user_id, "weekly", timestamp)
        if period == "monthly":
            return self._weekly_paths_for_month(user_id, timestamp)
        if period == "yearly":
            return self._monthly_paths_for_year(user_id, timestamp)
        return []

    def _weekly_paths_for_month(self, user_id: str, timestamp: datetime) -> List[Path]:
        user_dir = self._user_dir(user_id)
        if not user_dir.exists():
            return []
        target = self._local_date(timestamp)
        target_year = target.year
        target_month = target.month
        paths: List[Path] = []
        for path in sorted(user_dir.glob("??-Week??.md")):
            match = re.match(r"^(\\d{2})-Week(\\d{2})\\.md$", path.name)
            if not match:
                continue
            year = 2000 + int(match.group(1))
            week = int(match.group(2))
            try:
                week_start = date.fromisocalendar(year, week, 1)
            except ValueError:
                continue
            for offset in range(7):
                day = week_start + timedelta(days=offset)
                if day.year == target_year and day.month == target_month:
                    paths.append(path)
                    break
        return paths

    def _monthly_paths_for_year(self, user_id: str, timestamp: datetime) -> List[Path]:
        user_dir = self._user_dir(user_id)
        if not user_dir.exists():
            return []
        target_year = self._local_date(timestamp).year
        paths: List[Path] = []
        for path in sorted(user_dir.glob("??-??.md")):
            match = re.match(r"^(\\d{2})-(\\d{2})\\.md$", path.name)
            if not match:
                continue
            year = 2000 + int(match.group(1))
            if year != target_year:
                continue
            paths.append(path)
        return paths

    # ================================================================
    # Write helpers
    # ================================================================

    def _write_summary(
        self, user_id: str, period: str, summary: str, timestamp: datetime,
        session_id: Optional[str], meta: Optional[Dict[str, Any]],
    ) -> None:
        journal = self._journal(user_id)
        if period == "dialogue":
            if session_id:
                journal.append_session_summary(session_id, summary, summary_time=timestamp, meta=meta)
            return
        journal.append_period_summary(period, summary, summary_time=timestamp, meta=meta)

    def _write_dialogue_summary(
        self, user_id: str, session_id: str, summary: str,
        timestamp: datetime, meta: Optional[Dict[str, Any]],
    ) -> None:
        journal = self._journal(user_id)
        path = journal.append_session_summary(session_id, summary, summary_time=timestamp, meta=meta)
        logger.info("Wrote dialogue summary for session %s to %s", session_id[:8], path)

    def _write_user_updates(
        self, user_id: str, updates: Sequence[str], timestamp: datetime,
        session_id: Optional[str], meta: Optional[Dict[str, Any]],
    ) -> None:
        journal = self._journal(user_id)
        path = journal.append_user_memory(updates=updates, timestamp=timestamp, session_id=session_id, meta=meta)
        logger.info("Wrote %d user memory updates for %s to %s", len(updates), user_id, path)

    # ================================================================
    # Helpers
    # ================================================================

    def _period_key(self, period: str, timestamp: datetime) -> str:
        return self._period_key_from_date(period, self._local_date(timestamp))

    @staticmethod
    def _period_key_from_date(period: str, value: date) -> str:
        if period == "daily":
            return value.strftime("%y-%m-%d")
        if period == "weekly":
            iso = value.isocalendar()
            return f"{iso.year}-W{iso.week:02d}"
        if period == "monthly":
            return value.strftime("%y-%m")
        if period == "yearly":
            return value.strftime("%y")
        return ""

    def _local_date(self, timestamp: datetime) -> date:
        local = timestamp.astimezone(self._tzinfo) if self._tzinfo else timestamp.astimezone()
        return local.date()

    def _local_time(self, timestamp: datetime) -> str:
        local = timestamp.astimezone(self._tzinfo) if self._tzinfo else timestamp.astimezone()
        return local.strftime("%Y-%m-%d %H:%M")

    def _date_to_timestamp(self, value: date) -> datetime:
        tzinfo = self._tzinfo or timezone.utc
        return datetime(value.year, value.month, value.day, 12, 0, tzinfo=tzinfo)

    def _journal(self, user_id: str) -> RawMemoryJournal:
        safe = RawMemoryJournal._safe_user_id(user_id)
        cfg = RawMemoryConfig(
            base_dir=str(self._base_dir), user_id=safe,
            ai_name=self.config.raw_memory.ai_name,
            user_memory_file=self.config.raw_memory.user_memory_file,
            timezone=self.config.raw_memory.timezone,
        )
        return RawMemoryJournal(cfg)

    def _user_dir(self, user_id: str) -> Path:
        return self._base_dir / RawMemoryJournal._safe_user_id(user_id)

    @staticmethod
    def _parse_daily_filename(name: str) -> Optional[date]:
        match = re.match(r"^(\d{2})-(\d{2})-(\d{2})\.md$", name)
        if not match:
            return None
        try:
            return date(2000 + int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None

    @staticmethod
    def _strip_summary_sections(text: str) -> str:
        if not text:
            return ""
        lines = text.splitlines()
        stripped: List[str] = []
        skipping = False
        for line in lines:
            if line.startswith("### ") and "Summary" in line:
                skipping = True
                continue
            if skipping and (line.startswith("### ") or line.startswith("## ")):
                skipping = False
            if not skipping:
                stripped.append(line)
        return "\n".join(stripped).strip()

    @staticmethod
    def _extract_summary_blocks(text: str, heading: str) -> List[str]:
        if not text or not heading:
            return []
        lines = text.splitlines()
        blocks: List[str] = []
        collecting = False
        current: List[str] = []
        for line in lines:
            if line.startswith(heading):
                if current:
                    blocks.append("\n".join(current).strip())
                    current = []
                collecting = True
                continue
            if collecting and (line.startswith("### ") or line.startswith("## ") or line.startswith("# ")):
                blocks.append("\n".join(current).strip())
                current = []
                collecting = False
            if collecting:
                current.append(line)
        if collecting and current:
            blocks.append("\n".join(current).strip())
        return [b for b in blocks if b]

    @staticmethod
    def _extract_session_block(text: str, session_id: str) -> str:
        if not text or not session_id:
            return ""
        pattern = rf"^## Session {re.escape(session_id)}\b[\s\S]*?(?=^## Session |\Z)"
        match = re.search(pattern, text, flags=re.MULTILINE)
        return match.group(0).strip() if match else ""

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

    @staticmethod
    def _from_signal_ts(signal: Signal) -> datetime:
        return datetime.fromtimestamp(signal.timestamp, tz=timezone.utc)

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
        return self.config.raw_memory.user_id

    async def _read_file(self, path: Path) -> str:
        return await asyncio.to_thread(path.read_text, encoding="utf-8")
