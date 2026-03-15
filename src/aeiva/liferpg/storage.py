from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping

import yaml

from aeiva.liferpg.schema import default_liferpg_profile, normalize_profile


def _resolve_dir(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def default_radar_templates() -> Dict[str, Any]:
    return {
        "_level_schema": {
            "levels": ["L1", "L2", "L3", "L4", "L5"],
            "descriptions": {
                "L1": "novice",
                "L2": "practicing",
                "L3": "solid",
                "L4": "strong",
                "L5": "expert",
            },
        },
        "researcher": {
            "display_name": "Researcher",
            "dimensions": [
                "Problem Framing",
                "Method & Experiment",
                "Literature Synthesis",
                "Academic Writing",
                "Research Delivery",
            ],
        },
        "programmer": {
            "display_name": "Programmer",
            "dimensions": [
                "Problem Decomposition",
                "Code Quality",
                "Debugging",
                "Testing",
                "Delivery & Maintainability",
            ],
        },
        "ai_engineer": {
            "display_name": "AI Engineer",
            "dimensions": [
                "Modeling & Prompting",
                "Data & Evaluation",
                "System Integration",
                "Reliability & Safety",
                "Product Impact",
            ],
        },
    }


@dataclass
class LifeRPGStore:
    base_dir: str = "storage/liferpg"
    profile_filename: str = "liferpg.yaml"
    templates_filename: str = "radar_templates.yaml"
    history_filename: str = "history.md"
    state_filename: str = "runtime_state.yaml"

    def __post_init__(self) -> None:
        root = _resolve_dir(self.base_dir)
        self.root = root
        self.profile_path = root / self.profile_filename
        self.templates_path = root / self.templates_filename
        self.history_path = root / self.history_filename
        self.state_path = root / self.state_filename

    def ensure_initialized(self, *, default_profile: Mapping[str, Any] | None = None) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

        if not self.profile_path.exists():
            profile = default_liferpg_profile()
            if isinstance(default_profile, Mapping):
                profile = normalize_profile(default_profile)
            self.write_profile(profile)

        if not self.templates_path.exists():
            self.write_templates(default_radar_templates())

        if not self.history_path.exists():
            self.history_path.write_text("# LifeRPG Update History\n\n", encoding="utf-8")

        if not self.state_path.exists():
            self.write_runtime_state({"last_review": {}, "last_session_end": {}})

    def read_profile(self) -> Dict[str, Any]:
        if not self.profile_path.exists():
            return default_liferpg_profile()
        try:
            data = yaml.safe_load(self.profile_path.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
        if not isinstance(data, Mapping):
            data = {}
        return normalize_profile(data)

    def write_profile(self, profile: Mapping[str, Any]) -> None:
        normalized = normalize_profile(profile)
        text = yaml.safe_dump(
            normalized,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )
        self.profile_path.write_text(text, encoding="utf-8")

    def read_templates(self) -> Dict[str, Any]:
        if not self.templates_path.exists():
            return default_radar_templates()
        try:
            data = yaml.safe_load(self.templates_path.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
        if not isinstance(data, Mapping):
            return default_radar_templates()
        return dict(data)

    def write_templates(self, templates: Mapping[str, Any]) -> None:
        text = yaml.safe_dump(
            dict(templates),
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )
        self.templates_path.write_text(text, encoding="utf-8")

    def read_runtime_state(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return {"last_review": {}, "last_session_end": {}}
        try:
            data = yaml.safe_load(self.state_path.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
        if not isinstance(data, Mapping):
            return {"last_review": {}, "last_session_end": {}}
        state = dict(data)
        if not isinstance(state.get("last_review"), Mapping):
            state["last_review"] = {}
        if not isinstance(state.get("last_session_end"), Mapping):
            state["last_session_end"] = {}
        return state

    def write_runtime_state(self, state: Mapping[str, Any]) -> None:
        text = yaml.safe_dump(
            dict(state),
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )
        self.state_path.write_text(text, encoding="utf-8")

    def append_history(
        self,
        *,
        period: str,
        summary: str,
        changed_keys: list[str],
        timestamp: datetime | None = None,
    ) -> None:
        if not self.history_path.exists():
            self.history_path.write_text("# LifeRPG Update History\n\n", encoding="utf-8")
        ts = (timestamp or datetime.now().astimezone()).strftime("%Y-%m-%d %H:%M:%S")
        clean_summary = (summary or "").strip() or "(no summary)"
        key_text = ", ".join(changed_keys) if changed_keys else "(none)"
        with self.history_path.open("a", encoding="utf-8") as f:
            f.write(f"- [{ts}] period={period} keys={key_text} :: {clean_summary}\n")
