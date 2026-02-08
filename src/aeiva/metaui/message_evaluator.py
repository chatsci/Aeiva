from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .a2ui_protocol import ServerToClientEnvelope


def _is_json_pointer(path: Any) -> bool:
    if path is None:
        return True
    text = str(path).strip()
    return text == "/" or text.startswith("/")


def _extract_child_refs_from_mapping(component: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    child = component.get("child")
    if isinstance(child, str) and child.strip():
        refs.append(child.strip())

    children = component.get("children")
    if isinstance(children, list):
        refs.extend(str(item).strip() for item in children if str(item).strip())
    elif isinstance(children, Mapping):
        component_id = children.get("componentId")
        if isinstance(component_id, str) and component_id.strip():
            refs.append(component_id.strip())
        template = children.get("template")
        if isinstance(template, Mapping):
            template_id = template.get("componentId")
            if isinstance(template_id, str) and template_id.strip():
                refs.append(template_id.strip())
    return refs


@dataclass
class _SurfaceState:
    created: bool = False
    component_ids: set[str] = field(default_factory=set)
    has_component_update: bool = False
    has_root: bool = False


def _evaluate_v010_message(
    *,
    raw: Mapping[str, Any],
    index: int,
    surfaces: Dict[str, _SurfaceState],
    issues: List[str],
) -> bool:
    if "createSurface" in raw:
        payload = raw.get("createSurface")
        if not isinstance(payload, Mapping):
            issues.append(f"message[{index}] createSurface must be an object.")
            return True
        surface_id = str(payload.get("surfaceId") or "").strip()
        catalog_id = str(payload.get("catalogId") or "").strip()
        if not surface_id:
            issues.append(f"message[{index}] createSurface.surfaceId is required.")
            return True
        if not catalog_id:
            issues.append(f"message[{index}] createSurface.catalogId is required.")
            return True
        state = surfaces.setdefault(surface_id, _SurfaceState())
        state.created = True
        return True

    if "updateComponents" in raw:
        payload = raw.get("updateComponents")
        if not isinstance(payload, Mapping):
            issues.append(f"message[{index}] updateComponents must be an object.")
            return True
        surface_id = str(payload.get("surfaceId") or "").strip()
        if not surface_id:
            issues.append(f"message[{index}] updateComponents.surfaceId is required.")
            return True
        state = surfaces.get(surface_id)
        if state is None or not state.created:
            issues.append(
                f"message[{index}] updateComponents for '{surface_id}' before createSurface."
            )
            return True

        components = payload.get("components")
        if not isinstance(components, list) or not components:
            issues.append(f"message[{index}] updateComponents.components must be a non-empty array.")
            return True

        batch_ids: set[str] = set()
        for component in components:
            if not isinstance(component, Mapping):
                continue
            component_id = str(component.get("id") or "").strip()
            if not component_id:
                issues.append(f"message[{index}] component id is required.")
                continue
            batch_ids.add(component_id)
            if component_id == "root":
                state.has_root = True

        all_known_ids = set(state.component_ids) | batch_ids
        for component in components:
            if not isinstance(component, Mapping):
                continue
            for ref in _extract_child_refs_from_mapping(component):
                if ref not in all_known_ids:
                    issues.append(
                        f"message[{index}] missing child reference '{ref}' in surface '{surface_id}'."
                    )

        state.component_ids |= batch_ids
        state.has_component_update = True
        return True

    if "updateDataModel" in raw:
        payload = raw.get("updateDataModel")
        if not isinstance(payload, Mapping):
            issues.append(f"message[{index}] updateDataModel must be an object.")
            return True
        surface_id = str(payload.get("surfaceId") or "").strip()
        if not surface_id:
            issues.append(f"message[{index}] updateDataModel.surfaceId is required.")
            return True
        state = surfaces.get(surface_id)
        if state is None or not state.created:
            issues.append(
                f"message[{index}] updateDataModel for '{surface_id}' before createSurface."
            )
            return True
        path = payload.get("path", "/")
        if not _is_json_pointer(path):
            issues.append(
                f"message[{index}] updateDataModel.path must be a JSON Pointer (got '{path}')."
            )
        return True

    if "deleteSurface" in raw:
        payload = raw.get("deleteSurface")
        if not isinstance(payload, Mapping):
            issues.append(f"message[{index}] deleteSurface must be an object.")
            return True
        surface_id = str(payload.get("surfaceId") or "").strip()
        if not surface_id:
            issues.append(f"message[{index}] deleteSurface.surfaceId is required.")
            return True
        surfaces.pop(surface_id, None)
        return True

    return False


def _evaluate_lifecycle_message(
    *,
    envelope: ServerToClientEnvelope,
    index: int,
    surfaces: Dict[str, _SurfaceState],
    issues: List[str],
) -> None:
    if envelope.surfaceUpdate is not None:
        sid = envelope.surfaceUpdate.surfaceId
        state = surfaces.setdefault(sid, _SurfaceState())
        state.created = True
        state.has_component_update = True
        batch_ids: set[str] = set()
        for component in envelope.surfaceUpdate.components:
            batch_ids.add(component.id)
            if component.id == "root":
                state.has_root = True
        all_known_ids = set(state.component_ids) | batch_ids
        for component in envelope.surfaceUpdate.components:
            wrapper = component.component
            payload = next(iter(wrapper.values()), None)
            props = payload.props if payload is not None else {}
            for ref in _extract_child_refs_from_mapping(props):
                if ref not in all_known_ids:
                    issues.append(
                        f"message[{index}] missing child reference '{ref}' in surface '{sid}'."
                    )
        state.component_ids |= batch_ids
        return

    if envelope.beginRendering is not None:
        sid = envelope.beginRendering.surfaceId
        state = surfaces.setdefault(sid, _SurfaceState())
        if not state.has_component_update:
            issues.append(
                f"message[{index}] beginRendering for '{sid}' before any surfaceUpdate."
            )
            return
        root = envelope.beginRendering.root
        if root not in state.component_ids:
            issues.append(
                f"message[{index}] beginRendering root '{root}' not found in surface components for '{sid}'."
            )
        return

    if envelope.dataModelUpdate is not None:
        sid = envelope.dataModelUpdate.surfaceId
        state = surfaces.setdefault(sid, _SurfaceState())
        if not state.has_component_update:
            issues.append(
                f"message[{index}] dataModelUpdate for '{sid}' before surfaceUpdate."
            )
        if not _is_json_pointer(envelope.dataModelUpdate.path):
            issues.append(
                f"message[{index}] dataModelUpdate.path must be a JSON Pointer (got '{envelope.dataModelUpdate.path}')."
            )
        return

    if envelope.deleteSurface is not None:
        surfaces.pop(envelope.deleteSurface.surfaceId, None)


def evaluate_server_messages(messages: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    issues: List[str] = []
    surfaces: Dict[str, _SurfaceState] = {}
    message_count = 0

    for index, raw in enumerate(messages):
        message_count += 1
        if isinstance(raw, Mapping) and _evaluate_v010_message(
            raw=raw,
            index=index,
            surfaces=surfaces,
            issues=issues,
        ):
            continue

        try:
            envelope = ServerToClientEnvelope.model_validate(raw)
        except Exception as exc:
            issues.append(f"message[{index}] schema error: {exc}")
            continue
        _evaluate_lifecycle_message(
            envelope=envelope,
            index=index,
            surfaces=surfaces,
            issues=issues,
        )

    for surface_id, state in surfaces.items():
        if state.has_component_update and not state.has_root:
            issues.append(
                f"surface '{surface_id}' is missing required root component 'root'."
            )

    return {
        "valid": not issues,
        "issues": issues,
        "message_count": message_count,
    }
