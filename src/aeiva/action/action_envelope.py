"""
Action envelope utilities for JSON-only action proposals.

The LLM is instructed to return a single JSON object that follows a
lightweight, universal schema. This module parses and normalizes the
JSON output, and converts actions into internal Plan/Task structures.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from aeiva.action.plan import Plan
from aeiva.action.task import Task

logger = logging.getLogger(__name__)


ACTION_SYSTEM_PROMPT = """You must respond with a single JSON object and no other text.
Do NOT wrap the JSON in markdown code fences.

Schema:
{
  "type": "message" | "action" | "mixed",
  "message": "optional natural language response",
  "actions": [
    {
      "tool": "tool_name",
      "args": { "key": "value" },
      "id": "optional",
      "description": "optional",
      "depends_on": ["optional_step_id"],
      "actions": [ ... nested actions ... ]
    }
  ],
  "meta": {
    "reason": "optional",
    "confidence": 0.0
  }
}

Notes:
- "message" is optional. Use it for user-facing replies.
- Use "type" = "action" when you only need to run actions.
- Use "type" = "mixed" when you want to reply and run actions.
- Leave "actions" empty or omit it if no actions are needed.
"""

ACTION_SYSTEM_PROMPT_AUTO = """You may respond normally when no tools are needed.

If you need to use tools, respond with a single JSON object and no other text.
Do NOT wrap the JSON in markdown code fences.

Schema:
{
  "type": "message" | "action" | "mixed",
  "message": "optional natural language response",
  "actions": [
    {
      "tool": "tool_name",
      "args": { "key": "value" },
      "id": "optional",
      "description": "optional",
      "depends_on": ["optional_step_id"],
      "actions": [ ... nested actions ... ]
    }
  ],
  "meta": {
    "reason": "optional",
    "confidence": 0.0
  }
}

Notes:
- Use JSON only when actions are required.
- Use "type" = "action" when you only need to run actions.
- Use "type" = "mixed" when you want to reply and run actions.
- Leave "actions" empty or omit it if no actions are needed.
"""


def resolve_action_mode(action_cfg: Dict[str, Any]) -> str:
    """
    Resolve action mode from config.

    Returns:
        "json" - Force JSON output with action schema
        "auto" - Normal response, JSON only when tools needed
        "off"  - No action system
    """
    if not isinstance(action_cfg, dict):
        return "off"
    if not action_cfg.get("enabled", True):
        return "off"

    # Check explicit mode first
    mode = action_cfg.get("mode") or action_cfg.get("action_mode")
    if mode:
        mode = mode.lower()
        if mode in {"off", "disabled", "none"}:
            return "off"
        if mode in {"json", "tools", "auto"}:
            return mode

    # Legacy: force_json implies json mode
    if action_cfg.get("force_json", False):
        return "json"

    return "auto"


def parse_action_envelope(text: str) -> Tuple[Dict[str, Any], List[str]]:
    """Parse and normalize an action envelope from raw model text."""
    errors: List[str] = []
    raw_text = text or ""

    if isinstance(text, dict):
        return _normalize_envelope(text, raw_text), errors

    candidate = _extract_json_block(raw_text)
    if candidate is None:
        errors.append("no_json_found")
        return _normalize_envelope({}, raw_text), errors

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        errors.append(f"json_decode_error:{exc}")
        return _normalize_envelope({}, raw_text), errors

    if not isinstance(parsed, dict):
        errors.append("json_not_object")
        return _normalize_envelope({}, raw_text), errors

    return _normalize_envelope(parsed, raw_text), errors


def _extract_json_block(text: str) -> Optional[str]:
    """Extract the first JSON object from text, handling code fences."""
    if not text:
        return None

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    start = text.find("{")
    if start == -1:
        return None

    # Prefer a robust JSON decoder that can stop at the first valid object.
    try:
        decoder = json.JSONDecoder()
        _, end = decoder.raw_decode(text[start:])
        return text[start : start + end].strip()
    except json.JSONDecodeError:
        pass

    end = text.rfind("}")
    if end == -1 or end <= start:
        return None
    return text[start : end + 1].strip()


def _normalize_envelope(envelope: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
    """Normalize envelope fields with sensible defaults."""
    message = envelope.get("message")
    if message is None:
        message = envelope.get("text")
    if message is None:
        message = envelope.get("content")

    actions = envelope.get("actions")
    if actions is None:
        actions = envelope.get("action")
    if actions is None:
        actions = envelope.get("steps")
    if isinstance(actions, dict):
        actions = [actions]
    if actions is None:
        actions = []

    if not isinstance(actions, list):
        actions = []

    envelope_type = envelope.get("type")
    has_actions = bool(actions)
    has_message = bool(message)

    if envelope_type not in ("message", "action", "mixed"):
        if has_actions and has_message:
            envelope_type = "mixed"
        elif has_actions:
            envelope_type = "action"
        else:
            envelope_type = "message"

    if envelope_type == "message":
        actions = []

    meta = envelope.get("meta")
    if meta is None:
        meta = envelope.get("metadata")
    if not isinstance(meta, dict):
        meta = {}

    if not has_message and envelope_type == "message":
        message = raw_text.strip() if raw_text else ""

    return {
        "type": envelope_type,
        "message": message or "",
        "actions": actions,
        "meta": meta,
    }


def actions_to_plan(
    actions: List[Dict[str, Any]],
    *,
    name: str = "ActionPlan",
    plan_id: Optional[str] = None,
    description: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Plan:
    """Convert a list of action dicts into a Plan of Tasks (nested supported)."""
    steps: List[Any] = []
    metadata = metadata or {}
    known_ids = {a.get("id") for a in actions if isinstance(a, dict) and a.get("id")}

    for idx, action in enumerate(actions):
        if not isinstance(action, dict):
            logger.debug("Skipping non-dict action at index %s", idx)
            continue

        nested = action.get("actions") or action.get("steps")
        if nested:
            subplan = actions_to_plan(
                nested if isinstance(nested, list) else [],
                name=action.get("name") or action.get("tool") or f"Subplan-{idx}",
                plan_id=action.get("id"),
                description=action.get("description", ""),
                metadata=action.get("meta") or action.get("metadata"),
            )
            steps.append(subplan)
            continue

        tool = action.get("tool") or action.get("name") or action.get("action")
        if not tool:
            logger.debug("Skipping action without tool/name at index %s", idx)
            continue

        params = action.get("args") or action.get("params") or {}
        if not isinstance(params, dict):
            params = {}

        dependent_ids = action.get("depends_on") or action.get("dependent_ids") or []
        if isinstance(dependent_ids, list):
            dependent_ids = [d for d in dependent_ids if d in known_ids]
        else:
            dependent_ids = []

        task = Task(
            name=tool,
            params=params,
            id=action.get("id"),
            dependent_ids=dependent_ids,
            description=action.get("description", ""),
            metadata=action.get("meta") or action.get("metadata") or {},
        )
        steps.append(task)

    plan_kwargs = {
        "name": name,
        "steps": steps,
        "description": description,
        "metadata": metadata,
    }
    if plan_id:
        plan_kwargs["id"] = plan_id
    return Plan(**plan_kwargs)
