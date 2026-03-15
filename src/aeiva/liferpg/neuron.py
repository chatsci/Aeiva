from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from aeiva.event.event_names import EventNames
from aeiva.llm.llm_client import LLMClient
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.liferpg.schema import apply_merge_patch, normalize_profile
from aeiva.liferpg.storage import LifeRPGStore
from aeiva.neuron import BaseNeuron, NeuronConfig, Signal

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None


logger = logging.getLogger(__name__)


DEFAULT_INPUT_EVENTS = [
    EventNames.RAW_MEMORY_SESSION_CLOSED,
    EventNames.LIFERPG_QUERY,
    EventNames.LIFERPG_UPDATE,
]

DEFAULT_SYSTEM_PROMPT = (
    "You maintain a user's LifeRPG profile for a human-centered AI assistant. "
    "Given period context and current profile, decide if profile update is needed. "
    "Return JSON only. Format: "
    "{\"update\": false} OR {\"update\": true, \"summary\": \"...\", \"patch\": {...}}. "
    "The patch MUST be a minimal JSON merge patch to the root profile object. "
    "Prefer objective facts and stable updates. "
    "Do not invent private facts. "
    "No markdown, no code fences, no extra text."
)


@dataclass
class LifeRPGNeuronConfig(NeuronConfig):
    input_events: List[str] = field(default_factory=lambda: DEFAULT_INPUT_EVENTS.copy())
    output_event: str = EventNames.LIFERPG_CHANGED
    error_event: str = EventNames.LIFERPG_ERROR
    base_dir: str = "storage/liferpg"
    profile_filename: str = "liferpg.yaml"
    templates_filename: str = "radar_templates.yaml"
    history_filename: str = "history.md"
    state_filename: str = "runtime_state.yaml"
    raw_memory_base_dir: str = "storage/memory"
    user_id: str = "User"
    timezone: Optional[str] = None
    enabled: bool = True
    startup_catchup_enabled: bool = True
    llm_gateway_config: Dict[str, Any] = field(default_factory=dict)
    default_profile: Dict[str, Any] = field(default_factory=dict)
    decision_temperature: float = 0.2
    max_context_chars: int = 12000
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


class LifeRPGNeuron(BaseNeuron):
    EMISSIONS = [EventNames.LIFERPG_CHANGED, EventNames.LIFERPG_ERROR]
    CONFIG_CLASS = LifeRPGNeuronConfig

    def __init__(
        self,
        name: str = "liferpg",
        config: Optional[Dict[str, Any]] = None,
        event_bus: Optional[Any] = None,
        **kwargs,
    ):
        neuron_config = self.build_config(config or {})
        super().__init__(name=name, config=neuron_config, event_bus=event_bus, **kwargs)
        self.SUBSCRIPTIONS = self.config.input_events.copy()
        self.store = LifeRPGStore(
            base_dir=self.config.base_dir,
            profile_filename=self.config.profile_filename,
            templates_filename=self.config.templates_filename,
            history_filename=self.config.history_filename,
            state_filename=self.config.state_filename,
        )
        self._llm_client: Optional[LLMClient] = None
        self._tzinfo = self._resolve_timezone(self.config.timezone)
        self._runtime_state: Dict[str, Any] = {"last_review": {}, "last_session_end": {}}
        self._state_lock = asyncio.Lock()

    async def setup(self) -> None:
        await super().setup()
        self.store.ensure_initialized(default_profile=self.config.default_profile)
        self._runtime_state = self.store.read_runtime_state()
        if not self.config.enabled:
            self._llm_client = None
            return
        try:
            self._llm_client = self._build_llm_client(self.config.llm_gateway_config)
        except Exception as exc:
            logger.warning("LifeRPGNeuron disabled (LLM init failed): %s", exc)
            self._llm_client = None
        logger.info("%s setup complete", self.name)

    async def startup_catchup(self) -> Dict[str, Any]:
        if not self.config.enabled:
            return {"skipped": True, "reason": "disabled"}
        if not self.config.startup_catchup_enabled:
            return {"skipped": True, "reason": "startup_catchup_disabled"}

        now = datetime.now(timezone.utc)
        results: Dict[str, Any] = {"daily": False, "weekly": False, "monthly": False, "yearly": False}
        for period in ("daily", "weekly", "monthly", "yearly"):
            key = self._period_key(period, self._previous_period_time(period, now))
            last_key = str((self._runtime_state.get("last_review") or {}).get(period, ""))
            if key and key != last_key:
                result = await self._run_period_update(period=period, timestamp=self._previous_period_time(period, now))
                results[period] = bool(result.get("updated"))
                self._runtime_state.setdefault("last_review", {})[period] = key
        self.store.write_runtime_state(self._runtime_state)
        return results

    async def process(self, signal: Signal) -> Optional[Dict[str, Any]]:
        source = signal.source
        if source == EventNames.LIFERPG_QUERY:
            return self._handle_query()
        if source == EventNames.LIFERPG_UPDATE:
            return await self._handle_manual_update(signal)
        if source == EventNames.RAW_MEMORY_SESSION_CLOSED:
            return await self._handle_session_closed(signal)
        return None

    async def send(self, output: Any, parent: Signal = None) -> None:
        if output is None:
            return
        signal = parent.child(self.name, output) if parent else Signal(source=self.name, data=output)
        self.working.last_output = output
        if self.events:
            event_name = self.config.error_event if isinstance(output, Mapping) and output.get("error") else self.config.output_event
            emit_args = self.signal_to_event_args(event_name, signal)
            await self.events.emit(**emit_args)

    def _handle_query(self) -> Dict[str, Any]:
        return {
            "type": "state",
            "profile": self.store.read_profile(),
            "templates": self.store.read_templates(),
        }

    async def _handle_manual_update(self, signal: Signal) -> Dict[str, Any]:
        payload = signal.data if isinstance(signal.data, Mapping) else {}
        async with self._state_lock:
            profile = self.store.read_profile()
            if isinstance(payload.get("profile"), Mapping):
                updated = normalize_profile(payload.get("profile") or {})
            elif isinstance(payload.get("patch"), Mapping):
                updated = normalize_profile(apply_merge_patch(profile, payload.get("patch") or {}))
            else:
                return {"type": "updated", "updated": False, "period": "manual", "reason": "empty_payload"}

            changed_keys = self._changed_top_level_keys(profile, updated)
            if not changed_keys:
                return {"type": "updated", "updated": False, "period": "manual", "reason": "no_changes"}

            self.store.write_profile(updated)
            self.store.append_history(
                period="manual",
                summary=str(payload.get("summary") or "manual update"),
                changed_keys=changed_keys,
            )
            return {"type": "updated", "updated": True, "period": "manual", "changed_keys": changed_keys}

    async def _handle_session_closed(self, signal: Signal) -> Dict[str, Any]:
        payload = signal.data if isinstance(signal.data, Mapping) else {}
        user_id = self._extract_user_id(signal)
        timestamp = self._extract_datetime(payload.get("end_time")) or self._from_signal_ts(signal)
        session_text = str(payload.get("session_text") or payload.get("session_block") or "").strip()

        session_result = await self._run_period_update(
            period="session",
            timestamp=timestamp,
            user_id=user_id,
            context=session_text,
            session_id=str(payload.get("session_id") or ""),
        )

        rollover_periods: List[str] = []
        last_session_end = (self._runtime_state.get("last_session_end") or {}).get(user_id)
        previous_end = self._extract_datetime(last_session_end)
        if previous_end is not None:
            for period in ("daily", "weekly", "monthly", "yearly"):
                if self._period_key(period, previous_end) != self._period_key(period, timestamp):
                    rollover_result = await self._run_period_update(
                        period=period,
                        timestamp=previous_end,
                        user_id=user_id,
                    )
                    if rollover_result.get("updated"):
                        rollover_periods.append(period)
                    self._runtime_state.setdefault("last_review", {})[period] = self._period_key(period, previous_end)

        self._runtime_state.setdefault("last_session_end", {})[user_id] = timestamp.isoformat()
        self.store.write_runtime_state(self._runtime_state)

        result = dict(session_result)
        result["rollover_periods"] = rollover_periods
        return result

    async def _run_period_update(
        self,
        *,
        period: str,
        timestamp: datetime,
        user_id: Optional[str] = None,
        context: str = "",
        session_id: str = "",
    ) -> Dict[str, Any]:
        use_user_id = user_id or self.config.user_id
        context_text = context.strip()
        if not context_text and period != "session":
            context_text = self._load_period_context(
                period=period,
                user_id=use_user_id,
                timestamp=timestamp,
            )
        if not context_text:
            return {"type": "updated", "updated": False, "period": period, "reason": "empty_context"}

        decision = await self._decide_patch(
            period=period,
            timestamp=timestamp,
            user_id=use_user_id,
            session_id=session_id,
            profile=self.store.read_profile(),
            context=context_text,
        )

        if not decision.get("update"):
            return {"type": "updated", "updated": False, "period": period, "reason": "llm_skip"}

        patch = decision.get("patch")
        if not isinstance(patch, Mapping):
            return {"type": "updated", "updated": False, "period": period, "reason": "invalid_patch"}

        async with self._state_lock:
            latest_profile = self.store.read_profile()
            updated = normalize_profile(apply_merge_patch(latest_profile, patch))
            changed_keys = self._changed_top_level_keys(latest_profile, updated)
            if not changed_keys:
                return {"type": "updated", "updated": False, "period": period, "reason": "no_changes"}

            self.store.write_profile(updated)
            self.store.append_history(
                period=period,
                summary=str(decision.get("summary") or "profile updated"),
                changed_keys=changed_keys,
                timestamp=timestamp,
            )
        return {
            "type": "updated",
            "updated": True,
            "period": period,
            "changed_keys": changed_keys,
            "summary": str(decision.get("summary") or "").strip(),
        }

    async def _decide_patch(
        self,
        *,
        period: str,
        timestamp: datetime,
        user_id: str,
        session_id: str,
        profile: Mapping[str, Any],
        context: str,
    ) -> Dict[str, Any]:
        if self._llm_client is None:
            return {"update": False}

        context_text = context.strip()
        if self.config.max_context_chars and len(context_text) > self.config.max_context_chars:
            context_text = context_text[-self.config.max_context_chars :]

        header = (
            f"Period: {period}\n"
            f"Time: {self._local_time(timestamp)}\n"
            f"User: {user_id}"
        )
        if session_id:
            header += f"\nSession: {session_id}"

        payload = {
            "profile": profile,
            "context": context_text,
        }
        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {
                "role": "user",
                "content": f"{header}\n\n{json.dumps(payload, ensure_ascii=False)}",
            },
        ]

        try:
            raw = await self._llm_client.agenerate(messages)
        except Exception as exc:
            logger.warning("LifeRPG decision failed: %s", exc)
            return {"update": False}

        data = self._parse_json_object(str(raw or "").strip())
        if not isinstance(data, Mapping):
            return {"update": False}

        update = data.get("update", False)
        if isinstance(update, str):
            update = update.strip().lower() in {"1", "true", "yes", "on"}
        if not bool(update):
            return {"update": False}

        patch = data.get("patch")
        if not isinstance(patch, Mapping):
            return {"update": False}

        return {
            "update": True,
            "summary": str(data.get("summary") or "").strip(),
            "patch": dict(patch),
        }

    def _load_period_context(self, *, period: str, user_id: str, timestamp: datetime) -> str:
        user_dir = self._user_dir(user_id)
        if not user_dir.exists():
            return ""

        files: List[Path] = []
        local_dt = timestamp.astimezone(self._tzinfo) if self._tzinfo else timestamp.astimezone()
        yy = local_dt.strftime("%y")
        mm = local_dt.strftime("%m")
        dd = local_dt.strftime("%d")

        if period == "daily":
            files.append(user_dir / f"{yy}-{mm}-{dd}.md")
        elif period == "weekly":
            iso = local_dt.isocalendar()
            files.append(user_dir / f"{str(iso.year)[-2:]}-Week{iso.week:02d}.md")
            files.extend(self._daily_files_for_week(user_dir, iso.year, iso.week))
        elif period == "monthly":
            files.append(user_dir / f"{yy}-{mm}.md")
            files.extend(sorted(user_dir.glob(f"{yy}-{mm}-*.md")))
        elif period == "yearly":
            files.append(user_dir / f"{yy}.md")
            files.extend(sorted(user_dir.glob(f"{yy}-*.md")))
        else:
            return ""

        chunks: List[str] = []
        for path in files:
            if not path.exists() or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8").strip()
            except Exception:
                continue
            if text:
                chunks.append(f"# FILE: {path.name}\n{text}")
        return "\n\n".join(chunks)

    def _daily_files_for_week(self, user_dir: Path, year: int, week: int) -> List[Path]:
        results: List[Path] = []
        for path in sorted(user_dir.glob("??-??-??.md")):
            parsed = self._parse_daily_filename(path.name)
            if parsed is None:
                continue
            iso = parsed.isocalendar()
            if iso.year == year and iso.week == week:
                results.append(path)
        return results

    def _period_key(self, period: str, ts: datetime) -> str:
        local = ts.astimezone(self._tzinfo) if self._tzinfo else ts.astimezone()
        if period == "daily":
            return local.strftime("%Y-%m-%d")
        if period == "weekly":
            iso = local.isocalendar()
            return f"{iso.year}-W{iso.week:02d}"
        if period == "monthly":
            return local.strftime("%Y-%m")
        if period == "yearly":
            return local.strftime("%Y")
        if period == "session":
            return local.strftime("%Y-%m-%dT%H:%M")
        return ""

    def _previous_period_time(self, period: str, now: datetime) -> datetime:
        local = now.astimezone(self._tzinfo) if self._tzinfo else now.astimezone()
        if period == "daily":
            prev = local - timedelta(days=1)
            return prev.replace(hour=12, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        if period == "weekly":
            start = local - timedelta(days=local.weekday())
            prev = start - timedelta(days=1)
            return prev.replace(hour=12, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        if period == "monthly":
            first = local.replace(day=1)
            prev = first - timedelta(days=1)
            return prev.replace(hour=12, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        first = local.replace(month=1, day=1)
        prev = first - timedelta(days=1)
        return prev.replace(hour=12, minute=0, second=0, microsecond=0).astimezone(timezone.utc)

    @staticmethod
    def _parse_daily_filename(name: str) -> Optional[date]:
        match = re.fullmatch(r"(\d{2})-(\d{2})-(\d{2})\.md", name)
        if not match:
            return None
        yy, mm, dd = match.groups()
        year = 2000 + int(yy)
        try:
            return date(year, int(mm), int(dd))
        except Exception:
            return None

    def _extract_user_id(self, signal: Signal) -> str:
        payload = signal.data if isinstance(signal.data, Mapping) else {}
        value = payload.get("user_id") if isinstance(payload, Mapping) else None
        text = str(value).strip() if value is not None else ""
        return text or self.config.user_id

    @staticmethod
    def _safe_user_id(user_id: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", user_id or "")
        return safe or "user"

    def _user_dir(self, user_id: str) -> Path:
        base = Path(self.config.raw_memory_base_dir).expanduser()
        if not base.is_absolute():
            base = (Path.cwd() / base).resolve()
        return base / self._safe_user_id(user_id)

    def _local_time(self, ts: datetime) -> str:
        local = ts.astimezone(self._tzinfo) if self._tzinfo else ts.astimezone()
        return local.strftime("%Y-%m-%d %H:%M:%S %Z")

    @staticmethod
    def _extract_datetime(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str) and value.strip():
            text = value.strip().replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(text)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except Exception:
                return None
        return None

    @staticmethod
    def _from_signal_ts(signal: Signal) -> datetime:
        return datetime.fromtimestamp(signal.timestamp, tz=timezone.utc)

    @staticmethod
    def _changed_top_level_keys(before: Mapping[str, Any], after: Mapping[str, Any]) -> List[str]:
        changed: List[str] = []
        all_keys = set(before.keys()) | set(after.keys())
        for key in sorted(all_keys):
            if before.get(key) != after.get(key):
                changed.append(str(key))
        return changed

    @staticmethod
    def _parse_json_object(text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    @staticmethod
    def _resolve_timezone(name: Optional[str]):
        if not name:
            return None
        if ZoneInfo is None:
            return None
        try:
            return ZoneInfo(name)
        except Exception:
            return None

    def _build_llm_client(self, cfg: Dict[str, Any]) -> LLMClient:
        llm_api_key = cfg.get("llm_api_key")
        valid_keys = LLMGatewayConfig.__dataclass_fields__.keys()
        params = {k: v for k, v in cfg.items() if k in valid_keys}
        params["llm_api_key"] = llm_api_key
        params["llm_temperature"] = self.config.decision_temperature
        params["llm_use_async"] = True
        params["llm_stream"] = False
        return LLMClient(LLMGatewayConfig(**params))
