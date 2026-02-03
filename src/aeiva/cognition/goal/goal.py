"""
GoalNeuron: minimal goal state storage.

Goal state is structured text with three tiers:
- long_term
- short_term
- todo
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aeiva.neuron import BaseNeuron, NeuronConfig, Signal
from aeiva.event.event_names import EventNames
from aeiva.llm.llm_client import LLMClient
from aeiva.llm.llm_gateway_config import LLMGatewayConfig

logger = logging.getLogger(__name__)


DEFAULT_INPUT_EVENTS = [
    EventNames.PERCEPTION_OUTPUT,
    EventNames.COGNITION_THOUGHT,
    EventNames.GOAL_UPDATE,
    EventNames.GOAL_QUERY,
]

DEFAULT_SYSTEM_PROMPT = (
    "You update an AI agent's hierarchical goal list. "
    "Return ONLY a JSON object with optional keys: "
    "\"yearly\", \"monthly\", \"weekly\", \"daily\", \"session\". "
    "Each value must be an array of strings. "
    "For yearly/monthly/weekly/daily, return NEW items to append (do not repeat existing items). "
    "For session, return the FULL current session TODO list if it should change; "
    "otherwise omit the \"session\" key. "
    "If nothing should change, return {}. "
    "Most messages should NOT update goals; only update when clear tasks or plans appear. "
    "If you decide to update any period list, also update \"session\" to reflect current session tasks. "
    "No markdown, no code fences, no extra text."
)


TIER_ALIASES = {
    "long": "long_term",
    "long_term": "long_term",
    "short": "short_term",
    "short_term": "short_term",
    "todo": "todo",
}


@dataclass
class GoalState:
    long_term: List[str] = field(default_factory=list)
    short_term: List[str] = field(default_factory=list)
    todo: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, List[str]]:
        return {
            "long_term": list(self.long_term),
            "short_term": list(self.short_term),
            "todo": list(self.todo),
        }


@dataclass
class GoalNeuronConfig(NeuronConfig):
    input_events: List[str] = field(default_factory=lambda: DEFAULT_INPUT_EVENTS.copy())
    output_event: str = EventNames.GOAL_CHANGED
    default_tier: str = "short_term"
    base_dir: str = "storage/goal"
    goal_file: str = "Goal.md"
    llm_gateway_config: Dict[str, Any] = field(default_factory=dict)
    decision_temperature: float = 0.2
    decision_max_chars: int = 4000
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


class GoalNeuron(BaseNeuron):
    """Single goal neuron with hierarchical TODO state."""

    EMISSIONS = [
        EventNames.GOAL_CHANGED,
        EventNames.GOAL_ERROR,
    ]
    CONFIG_CLASS = GoalNeuronConfig

    def __init__(
        self,
        name: str = "goal",
        config: Optional[Dict[str, Any]] = None,
        event_bus: Optional[Any] = None,
        **kwargs,
    ):
        neuron_config = self.build_config(config or {})
        super().__init__(name=name, config=neuron_config, event_bus=event_bus, **kwargs)
        self.SUBSCRIPTIONS = self.config.input_events.copy()
        self.state = GoalState()
        self._journal = GoalJournal(self.config.base_dir, self.config.goal_file)
        self._llm_client: Optional[LLMClient] = None
        self._last_user_input: Optional[str] = None

    async def setup(self) -> None:
        await super().setup()
        self._journal.ensure()
        self.state = self._journal.load_state()
        self._journal.update_current_session([])  # New session starts clean
        try:
            self._llm_client = self._build_llm_client(self.config.llm_gateway_config)
        except Exception as exc:
            logger.warning("GoalNeuron disabled (LLM init failed): %s", exc)
            self._llm_client = None
        logger.info(
            "%s setup complete (long_term=%d, short_term=%d)",
            self.name, len(self.state.long_term), len(self.state.short_term),
        )

    def create_event_callback(self, pattern: str):
        async def on_event(event: "Event") -> None:
            if not self.accepting:
                return
            payload = event.payload
            if isinstance(payload, dict) and payload.get("streaming") and not payload.get("final"):
                return
            if isinstance(payload, Signal):
                data = payload.data
                if isinstance(data, dict) and data.get("streaming") and not data.get("final"):
                    return
            signal = self.event_to_signal(event)
            await self.enqueue(signal)

        on_event.__name__ = f"{self.name}_on_{pattern.replace('*', 'any').replace('.', '_')}"
        return on_event

    async def process(self, signal: Signal) -> Optional[Dict[str, Any]]:
        source = signal.source
        if EventNames.GOAL_UPDATE in source:
            return self.handle_update(signal)
        if EventNames.GOAL_QUERY in source:
            return self.handle_query(signal)
        if source.startswith("perception"):
            text = self._extract_text(signal.data)
            if text:
                self._last_user_input = text
            return None
        text = self._extract_text(signal.data)
        if not text:
            return None
        updates = await self._apply_text(text, signal)
        if not updates:
            return None
        return {
            "type": "updated",
            "state": self.state.as_dict(),
            "updates": updates,
        }

    def handle_query(self, signal: Signal) -> Dict[str, Any]:
        data = self._as_dict(signal.data)
        tier = data.get("tier")
        if tier:
            normalized = self._normalize_tier(str(tier))
            return {
                "type": "tier",
                "tier": normalized,
                "items": list(self._tier_list(normalized)),
            }
        return {
            "type": "state",
            "state": self.state.as_dict(),
        }

    def handle_update(self, signal: Signal) -> Dict[str, Any]:
        data = self._as_dict(signal.data)
        state = data.get("state")
        if isinstance(state, dict):
            self._apply_state_dict(state)
        else:
            self._apply_state_dict(data)
        return {
            "type": "updated",
            "state": self.state.as_dict(),
        }

    async def send(self, output: Any, parent: Signal = None) -> None:
        if output is None:
            return
        signal = parent.child(self.name, output) if parent else Signal(source=self.name, data=output)
        self.working.last_output = output
        if self.events:
            emit_args = self.signal_to_event_args(self.config.output_event, signal)
            await self.events.emit(**emit_args)

    def health_check(self) -> dict:
        """Return health status."""
        health = super().health_check()
        health["state"] = self.state.as_dict()
        health["journal_path"] = str(self._journal._path)
        health["llm_available"] = self._llm_client is not None
        return health

    def _apply_state_dict(self, data: Dict[str, Any]) -> None:
        if "long_term" in data:
            self.state.long_term = self._coerce_list(data.get("long_term"))
        if "short_term" in data:
            self.state.short_term = self._coerce_list(data.get("short_term"))
        if "todo" in data:
            self.state.todo = self._coerce_list(data.get("todo"))

    def _tier_list(self, tier: str) -> List[str]:
        normalized = self._normalize_tier(tier)
        if normalized == "long_term":
            return self.state.long_term
        if normalized == "short_term":
            return self.state.short_term
        return self.state.todo

    @staticmethod
    def _normalize_tier(tier: str) -> str:
        return TIER_ALIASES.get(str(tier).lower(), "short_term")

    @staticmethod
    def _as_dict(data: Any) -> Dict[str, Any]:
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _coerce_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item]
        if isinstance(value, str):
            return [value]
        return [str(value)]

    async def _apply_text(self, text: str, signal: Signal) -> List[Dict[str, Any]]:
        llm_updates = await self._llm_decide_updates(text, signal)
        if not llm_updates:
            return []
        update_records: List[Dict[str, Any]] = []
        now = datetime.now().astimezone()
        for period in ("yearly", "monthly", "weekly", "daily"):
            items = self._clean_items(llm_updates.get(period, []))
            if not items:
                continue
            key = self._period_key(period, now)
            if not key:
                continue
            for item in items:
                self._journal.append_period_item(period, key, item)
                update_records.append({"period": period, "key": key, "item": item})
            self._merge_state(period, items)
        if "session" in llm_updates:
            session_items = self._clean_items(llm_updates.get("session", []))
            self.state.todo = list(session_items)
            self._journal.update_current_session(session_items)
            update_records.append({"period": "session", "items": list(session_items)})
        return update_records

    @staticmethod
    def _normalize_item(item: str) -> str:
        return " ".join(item.strip().lower().split())

    @staticmethod
    def _extract_text(data: Any) -> Optional[str]:
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            if data.get("streaming") and not data.get("final"):
                return None
            if data.get("final") and isinstance(data.get("full_thought"), str):
                return data.get("full_thought")
            for key in ("text", "content", "data", "thought", "output"):
                if key in data and isinstance(data[key], str):
                    return data[key]
        if hasattr(data, "data"):
            return GoalNeuron._extract_text(getattr(data, "data"))
        if hasattr(data, "signals"):
            parts: List[str] = []
            for item in getattr(data, "signals", []) or []:
                text = GoalNeuron._extract_text(item)
                if text:
                    parts.append(text)
            return " ".join(parts) if parts else None
        return None

    @staticmethod
    def _clean_items(items: List[str]) -> List[str]:
        return [str(item).strip() for item in items if str(item).strip()]

    def _merge_state(self, period: str, items: List[str]) -> None:
        if not items:
            return
        if period == "yearly":
            target = self.state.long_term
        else:
            target = self.state.short_term
        seen = {self._normalize_item(item) for item in target if item}
        for item in items:
            normalized = self._normalize_item(item)
            if not normalized or normalized in seen:
                continue
            target.append(item)
            seen.add(normalized)

    @staticmethod
    def _period_key(period: str, now: datetime) -> str:
        if period == "yearly":
            return now.strftime("%Y")
        if period == "monthly":
            return now.strftime("%Y-%m")
        if period == "weekly":
            iso = now.isocalendar()
            return f"{iso.year}-Week{iso.week:02d}"
        if period == "daily":
            return now.strftime("%Y-%m-%d")
        return ""

    def _build_llm_client(self, cfg: Dict[str, Any]) -> LLMClient:
        llm_api_key = cfg.get("llm_api_key")
        valid_keys = LLMGatewayConfig.__dataclass_fields__.keys()
        params = {k: v for k, v in cfg.items() if k in valid_keys}
        params["llm_api_key"] = llm_api_key
        params["llm_temperature"] = self.config.decision_temperature
        params["llm_use_async"] = True
        params["llm_stream"] = False
        return LLMClient(LLMGatewayConfig(**params))

    async def _llm_decide_updates(self, text: str, signal: Signal) -> Dict[str, List[str]]:
        if not self._llm_client:
            return {}
        context = self._compose_context(signal)
        if not context:
            return {}
        content = context.strip()
        if not content:
            return {}
        max_chars = self.config.decision_max_chars
        if max_chars and len(content) > max_chars:
            content = content[-max_chars:]
        now = datetime.now().astimezone()
        messages = self._build_messages(content, signal, now)
        try:
            response = await self._llm_client.agenerate(messages)
        except Exception as exc:
            logger.warning("Goal LLM call failed: %s", exc)
            return {}
        return self._parse_llm_response(response)

    def _build_messages(
        self, text: str, signal: Signal, now: datetime,
    ) -> List[Dict[str, str]]:
        session_block = "\n".join(f"- {item}" for item in self.state.todo) or "(empty)"
        header = (
            f"Time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            f"Source: {signal.source}\n"
            f"Current session goals:\n{session_block}"
        )
        return [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": f"{header}\n\nMessage:\n{text}"},
        ]

    def _compose_context(self, signal: Signal) -> Optional[str]:
        data = signal.data
        if isinstance(data, dict):
            user_input = data.get("input") or data.get("user_input")
            assistant = data.get("full_thought") or data.get("thought") or data.get("output")
            if user_input and assistant:
                self._last_user_input = None
                return f"User: {user_input}\nAssistant: {assistant}"
        text = self._extract_text(data)
        if not text:
            return None
        if signal.source.startswith("cognition") and self._last_user_input:
            context = f"User: {self._last_user_input}\nAssistant: {text}"
            self._last_user_input = None
            return context
        return text

    @staticmethod
    def _parse_llm_response(response: str) -> Dict[str, List[str]]:
        if not response:
            return {}
        data = GoalNeuron._parse_json_object(response.strip())
        if data is None:
            logger.warning("Goal LLM returned non-JSON response")
            return {}
        if not isinstance(data, dict):
            return {}
        updates: Dict[str, List[str]] = {}
        allowed = {"yearly", "monthly", "weekly", "daily", "session"}
        for key, value in data.items():
            if key not in allowed:
                continue
            if value is None:
                items: List[str] = []
            elif isinstance(value, list):
                items = [str(item).strip() for item in value if str(item).strip()]
            elif isinstance(value, str):
                items = [value.strip()] if value.strip() else []
            else:
                continue
            if key == "session" or items:
                updates[key] = items
        return updates

    @staticmethod
    def _parse_json_object(text: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                return None


class GoalJournal:
    SECTION_ORDER = [
        "## Yearly Goals",
        "## Monthly Goals",
        "## Weekly Goals",
        "## Daily Goals",
        "## Current Session Goals",
    ]

    def __init__(self, base_dir: str, filename: str):
        self._base_dir = Path(base_dir).expanduser()
        if not self._base_dir.is_absolute():
            self._base_dir = (Path.cwd() / self._base_dir).resolve()
        self._path = self._base_dir / filename

    def ensure(self) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("# Goals\n\n", encoding="utf-8")
        text = self._path.read_text(encoding="utf-8")
        updated = self._ensure_sections(text)
        if updated != text:
            self._write(updated)

    def load_state(self) -> GoalState:
        """Parse Goal.md and return a GoalState reflecting current goals."""
        if not self._path.exists():
            return GoalState()
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError:
            return GoalState()
        lines = text.splitlines()
        long_term = self._all_section_items(lines, "## Yearly Goals")
        short_term = (
            self._latest_subsection_items(lines, "## Monthly Goals")
            + self._latest_subsection_items(lines, "## Weekly Goals")
        )
        # Deduplicate short_term preserving order
        seen: set = set()
        deduped: List[str] = []
        for item in short_term:
            norm = self._normalize_line(f"- {item}")
            if norm not in seen:
                seen.add(norm)
                deduped.append(item)
        # Session goals start empty — new session each launch
        return GoalState(long_term=long_term, short_term=deduped, todo=[])

    def _all_section_items(self, lines: List[str], heading: str) -> List[str]:
        """Extract all bullet items from every subsection of a section."""
        start, end = self._find_section(lines, heading)
        if start is None:
            return []
        return [line.strip()[2:] for line in lines[start:end] if line.strip().startswith("- ")]

    def _latest_subsection_items(self, lines: List[str], heading: str) -> List[str]:
        """Extract items from the most recent (last) ### subsection."""
        start, end = self._find_section(lines, heading)
        if start is None:
            return []
        last_sub = None
        for i in range(start, end):
            if lines[i].startswith("### "):
                last_sub = i + 1
        if last_sub is None:
            return self._all_section_items(lines, heading)
        return [line.strip()[2:] for line in lines[last_sub:end] if line.strip().startswith("- ")]

    def append_period_item(self, period: str, key: str, item: str) -> None:
        text = self._path.read_text(encoding="utf-8")
        text = self._ensure_sections(text)
        heading = self._section_heading(period)
        if not heading:
            return
        lines = text.splitlines()
        start, end = self._find_section(lines, heading)
        if start is None:
            return
        subheading = f"### {key}"
        sub_start, sub_end = self._find_subsection(lines, start, end, subheading)
        if sub_start is None:
            insert_at = end
            lines.insert(insert_at, "")
            lines.insert(insert_at + 1, subheading)
            lines.insert(insert_at + 2, f"- {item}")
            text = "\n".join(lines) + "\n"
            self._write(text)
            return
        block = lines[sub_start:sub_end]
        if any(self._normalize_line(line) == self._normalize_line(f"- {item}") for line in block):
            return
        lines.insert(sub_end, f"- {item}")
        text = "\n".join(lines) + "\n"
        self._write(text)

    def update_current_session(self, items: List[str]) -> None:
        text = self._path.read_text(encoding="utf-8")
        text = self._ensure_sections(text)
        lines = text.splitlines()
        heading = "## Current Session Goals"
        start, end = self._find_section(lines, heading)
        if start is None:
            return
        new_block = [heading, ""] + [f"- {item}" for item in items]
        new_block.append("")
        updated_lines = lines[:start - 1] + new_block + lines[end:]
        text = "\n".join(updated_lines).rstrip() + "\n"
        self._write(text)

    def _ensure_sections(self, text: str) -> str:
        lines = text.splitlines()
        if not lines or not lines[0].startswith("# "):
            lines = ["# Goals", ""] + lines
        existing = set(lines)
        for heading in self.SECTION_ORDER:
            if heading not in existing:
                if lines and lines[-1] != "":
                    lines.append("")
                lines.append(heading)
                lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def _write(self, text: str) -> None:
        normalized = self._normalize_spacing(text)
        self._path.write_text(normalized, encoding="utf-8")

    @staticmethod
    def _normalize_spacing(text: str) -> str:
        lines = text.splitlines()
        out: List[str] = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("## "):
                if out and out[-1] != "":
                    out.append("")
                out.append(line.rstrip())
                if i + 1 < len(lines) and lines[i + 1].strip() != "":
                    out.append("")
                continue
            if stripped.startswith("### "):
                if out and out[-1] != "":
                    out.append("")
                out.append(line.rstrip())
                continue
            if stripped == "":
                if out and out[-1] == "":
                    continue
                out.append("")
                continue
            out.append(line.rstrip())
        cleaned: List[str] = []
        for i, line in enumerate(out):
            if line == "" and cleaned:
                prev = cleaned[-1].lstrip()
                next_line = ""
                for j in range(i + 1, len(out)):
                    if out[j] != "":
                        next_line = out[j].lstrip()
                        break
                if prev.startswith("- ") and next_line.startswith("- "):
                    continue
            cleaned.append(line)
        return "\n".join(cleaned).rstrip() + "\n"

    @staticmethod
    def _section_heading(period: str) -> Optional[str]:
        mapping = {
            "yearly": "## Yearly Goals",
            "monthly": "## Monthly Goals",
            "weekly": "## Weekly Goals",
            "daily": "## Daily Goals",
        }
        return mapping.get(period)

    @staticmethod
    def _find_section(lines: List[str], heading: str) -> Tuple[Optional[int], Optional[int]]:
        try:
            idx = lines.index(heading)
        except ValueError:
            return None, None
        start = idx + 1
        end = len(lines)
        for i in range(start, len(lines)):
            if lines[i].startswith("## ") and lines[i] != heading:
                end = i
                break
        return start, end

    @staticmethod
    def _find_subsection(
        lines: List[str], start: int, end: int, heading: str,
    ) -> Tuple[Optional[int], Optional[int]]:
        for i in range(start, end):
            if lines[i] == heading:
                sub_start = i + 1
                sub_end = end
                for j in range(sub_start, end):
                    if lines[j].startswith("### ") and lines[j] != heading:
                        sub_end = j
                        break
                return sub_start, sub_end
        return None, None

    @staticmethod
    def _normalize_line(line: str) -> str:
        return " ".join(line.strip().lower().split())
