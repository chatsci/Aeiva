from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

from .intent_spec import intent_has_component_signals


_STRUCTURAL_OPS = frozenset(
    {
        "replace_spec",
        "merge_spec",
        "set_root",
        "append_component",
        "remove_component",
    }
)


@dataclass(frozen=True)
class PatchRoutingDecision:
    route_to_render_full: bool
    reason: str
    intent_text: Optional[str] = None


def _merge_dicts(base: Mapping[str, Any], incoming: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = deepcopy(dict(base))
    for key, value in incoming.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[key] = _merge_dicts(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def _merge_component_list(base_components: list[Any], incoming_components: list[Any]) -> list[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    order: list[str] = []

    def _ingest(component: Any) -> None:
        if not isinstance(component, Mapping):
            return
        component_id = str(component.get("id") or "").strip()
        if not component_id:
            return
        if component_id not in merged:
            merged[component_id] = deepcopy(dict(component))
            order.append(component_id)
            return
        merged[component_id] = _merge_dicts(merged[component_id], component)

    for component in base_components:
        _ingest(component)
    for component in incoming_components:
        _ingest(component)

    return [merged[component_id] for component_id in order]


def _sanitize_root(root: Any, components: list[Mapping[str, Any]]) -> list[str]:
    valid_ids = {
        str(component.get("id") or "").strip()
        for component in components
        if isinstance(component, Mapping)
    }
    valid_ids.discard("")
    if isinstance(root, list):
        normalized = []
        for item in root:
            token = str(item or "").strip()
            if token and token in valid_ids and token not in normalized:
                normalized.append(token)
        if normalized:
            return normalized
    return [item for item in valid_ids]


def _patch_has_structural_payload(patch: Mapping[str, Any]) -> bool:
    op = str(patch.get("op") or "").strip().lower()
    if op in _STRUCTURAL_OPS:
        return True
    if isinstance(patch.get("components"), list) or isinstance(patch.get("root"), list):
        return True
    spec = patch.get("spec")
    if isinstance(spec, Mapping):
        if isinstance(spec.get("components"), list) or isinstance(spec.get("root"), list):
            return True
    return False


def extract_structural_intent_text(patch: Mapping[str, Any]) -> Optional[str]:
    candidates: list[str] = []

    def _append(value: Any) -> None:
        text = str(value or "").strip()
        if text:
            candidates.append(text)

    def _append_text_fields(block: Any) -> None:
        if not isinstance(block, Mapping):
            return
        for key in ("title", "text", "description", "label", "placeholder", "message", "prompt", "intent"):
            _append(block.get(key))

    _append_text_fields(patch)
    _append_text_fields(patch.get("props"))
    _append_text_fields(patch.get("component"))
    component = patch.get("component")
    if isinstance(component, Mapping):
        _append_text_fields(component.get("props"))
    if str(patch.get("op") or "").strip().lower() == "merge_spec":
        _append_text_fields(patch.get("spec"))

    for text in candidates:
        if intent_has_component_signals(text):
            return text
    return None


def decide_patch_routing(patch: Mapping[str, Any]) -> PatchRoutingDecision:
    if _patch_has_structural_payload(patch):
        return PatchRoutingDecision(
            route_to_render_full=True,
            reason="patch_contains_structural_payload",
            intent_text=None,
        )

    intent_text = extract_structural_intent_text(patch)
    if intent_text:
        return PatchRoutingDecision(
            route_to_render_full=True,
            reason="intent_signals_structure_switch",
            intent_text=intent_text,
        )

    return PatchRoutingDecision(
        route_to_render_full=False,
        reason="patch_safe_for_incremental",
        intent_text=None,
    )


def apply_structural_patch_to_spec(
    base_spec: Mapping[str, Any],
    patch: Mapping[str, Any],
) -> Dict[str, Any]:
    current = deepcopy(dict(base_spec))
    current_components = current.get("components")
    if not isinstance(current_components, list):
        current_components = []
    current["components"] = deepcopy(current_components)
    current_root = current.get("root")
    if not isinstance(current_root, list):
        current_root = []
    current["root"] = [str(item) for item in current_root if str(item).strip()]

    op = str(patch.get("op") or "").strip().lower()
    patch_spec = patch.get("spec")

    if op == "replace_spec" and isinstance(patch_spec, Mapping):
        replaced = deepcopy(dict(patch_spec))
        components = replaced.get("components")
        if not isinstance(components, list):
            replaced["components"] = []
        root = replaced.get("root")
        replaced["root"] = _sanitize_root(root, replaced["components"])
        return replaced

    if op == "merge_spec" and isinstance(patch_spec, Mapping):
        merged = _merge_dicts(current, patch_spec)
        base_components = current.get("components")
        incoming_components = patch_spec.get("components")
        if isinstance(base_components, list) and isinstance(incoming_components, list):
            merged["components"] = _merge_component_list(base_components, incoming_components)
        if isinstance(patch_spec.get("root"), list):
            merged["root"] = [str(item) for item in patch_spec["root"] if str(item).strip()]
        merged["root"] = _sanitize_root(merged.get("root"), merged.get("components") or [])
        return merged

    components = deepcopy(current.get("components") or [])
    by_id: Dict[str, Dict[str, Any]] = {}
    order: list[str] = []
    for component in components:
        if not isinstance(component, Mapping):
            continue
        component_id = str(component.get("id") or "").strip()
        if not component_id:
            continue
        by_id[component_id] = deepcopy(dict(component))
        order.append(component_id)

    if op == "set_root" and isinstance(patch.get("root"), list):
        current["root"] = [str(item) for item in patch["root"] if str(item).strip()]
    elif op == "append_component" and isinstance(patch.get("component"), Mapping):
        component = deepcopy(dict(patch["component"]))
        component_id = str(component.get("id") or "").strip()
        if component_id:
            if component_id not in by_id:
                order.append(component_id)
                by_id[component_id] = component
            else:
                by_id[component_id] = _merge_dicts(by_id[component_id], component)
    elif op == "remove_component":
        target_id = str(patch.get("id") or "").strip()
        if target_id and target_id in by_id:
            by_id.pop(target_id, None)
            order = [item for item in order if item != target_id]
            current["root"] = [item for item in current["root"] if item != target_id]
    elif op == "update_component":
        target_id = str(patch.get("id") or "").strip()
        if not target_id and isinstance(patch.get("component"), Mapping):
            target_id = str(patch["component"].get("id") or "").strip()
        if target_id:
            updated = deepcopy(by_id.get(target_id, {"id": target_id}))
            component_block = patch.get("component")
            if isinstance(component_block, Mapping):
                updated = _merge_dicts(updated, component_block)
            patch_type = patch.get("type")
            if patch_type is not None:
                updated["type"] = patch_type
            patch_props = patch.get("props")
            if isinstance(patch_props, Mapping):
                updated["props"] = _merge_dicts(updated.get("props") or {}, patch_props)
            if target_id not in by_id:
                order.append(target_id)
            by_id[target_id] = updated
    elif op == "set_title":
        title = patch.get("title")
        if title is not None:
            current["title"] = str(title)

    current["components"] = [by_id[item] for item in order if item in by_id]
    current["root"] = _sanitize_root(current.get("root"), current["components"])
    return current
