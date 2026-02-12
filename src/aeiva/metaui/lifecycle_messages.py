from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from .capabilities import build_catalog_snapshot
from .component_catalog import get_component_catalog
from .protocol import MetaUISpec

A2UI_SERVER_MESSAGE_VERSION = "v0.10"


def _with_version(payload: Dict[str, Any]) -> Dict[str, Any]:
    message = dict(payload)
    message["version"] = A2UI_SERVER_MESSAGE_VERSION
    return message


def _to_surface_component(component: Mapping[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "id": str(component.get("id") or ""),
        "component": str(component.get("type") or "Text"),
    }
    props = component.get("props")
    if isinstance(props, Mapping):
        for key, value in props.items():
            payload[str(key)] = value
    return payload


def _component_payloads_for_update(spec: MetaUISpec) -> List[Dict[str, Any]]:
    payload = spec.model_dump(mode="json")
    raw_components = payload.get("components") if isinstance(payload, dict) else []
    normalized_components = [
        item for item in (raw_components or []) if isinstance(item, Mapping)
    ]
    root_ids = [str(item).strip() for item in (spec.root or []) if str(item).strip()]
    root_set = set(root_ids)
    root_first_components: List[Mapping[str, Any]] = []
    for root_id in root_ids:
        for component in normalized_components:
            if str(component.get("id") or "").strip() == root_id:
                root_first_components.append(component)
                break
    ordered_components = root_first_components + [
        component
        for component in normalized_components
        if str(component.get("id") or "").strip() not in root_set
    ]
    # Strict A2UI transport expects one canonical root.
    # Always expose one explicit wrapper root when the MetaUI root set is not exactly ["root"].
    should_wrap_root = len(root_ids) != 1 or root_ids[0] != "root"
    if should_wrap_root:
        used_ids = {
            str(component.get("id") or "").strip()
            for component in normalized_components
            if str(component.get("id") or "").strip()
        }
        synthetic_root_id = "root"
        if synthetic_root_id in used_ids:
            synthetic_root_id = "__metaui_root__"
            suffix = 2
            while synthetic_root_id in used_ids:
                synthetic_root_id = f"__metaui_root_{suffix}__"
                suffix += 1
        synthetic_root_component: Dict[str, Any] = {
            "id": synthetic_root_id,
            "type": "Column",
            "props": {"children": root_ids},
        }
        ordered_components = [synthetic_root_component] + ordered_components
    return [_to_surface_component(item) for item in ordered_components]


def build_create_surface_message(spec: MetaUISpec, *, catalog_id: Optional[str] = None) -> Dict[str, Any]:
    resolved_catalog_id = catalog_id
    if not resolved_catalog_id:
        resolved_catalog_id = build_catalog_snapshot(get_component_catalog())["catalogId"]
    payload: Dict[str, Any] = {
        "createSurface": {
            "surfaceId": spec.ui_id,
            "catalogId": resolved_catalog_id,
            "sendDataModel": bool(spec.send_data_model),
        }
    }
    if isinstance(spec.theme, Mapping) and spec.theme:
        payload["createSurface"]["theme"] = dict(spec.theme)
    return _with_version(payload)


def build_surface_update_message(spec: MetaUISpec) -> Dict[str, Any]:
    return _with_version(
        {
            "updateComponents": {
                "surfaceId": spec.ui_id,
                "components": _component_payloads_for_update(spec),
            }
        }
    )


def build_data_model_update_message(
    *,
    surface_id: str,
    state_patch: Mapping[str, Any],
    path: str = "/",
) -> Dict[str, Any]:
    return _with_version(
        {
            "updateDataModel": {
                "surfaceId": str(surface_id),
                "path": str(path or "/"),
                "value": dict(state_patch),
            }
        }
    )


def build_delete_surface_message(*, surface_id: str) -> Dict[str, Any]:
    return _with_version({"deleteSurface": {"surfaceId": str(surface_id)}})


def build_ui_render_sequence(
    *,
    spec: MetaUISpec,
    state: Optional[Mapping[str, Any]] = None,
    catalog_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    sequence: List[Dict[str, Any]] = [build_create_surface_message(spec, catalog_id=catalog_id)]
    sequence.append(build_surface_update_message(spec))
    if state:
        sequence.append(
            build_data_model_update_message(
                surface_id=spec.ui_id,
                state_patch=state,
                path="/",
            )
        )
    return sequence
