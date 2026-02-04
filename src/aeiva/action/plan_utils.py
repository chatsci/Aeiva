"""Utilities for building action Plans from action dicts."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from aeiva.action.plan import Plan
from aeiva.action.task import Task

logger = logging.getLogger(__name__)


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
