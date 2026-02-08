from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from .capabilities import build_catalog_snapshot
from .component_catalog import get_component_catalog
from .data_model import encode_object_to_contents
from .protocol import MetaUISpec


def _to_surface_component(component: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(component.get("id") or ""),
        "component": {
            "MetaUI": {
                "type": str(component.get("type") or "text"),
                "props": dict(component.get("props") or {}),
            }
        },
    }


def build_surface_update_message(spec: MetaUISpec) -> Dict[str, Any]:
    payload = spec.model_dump(mode="json")
    components = payload.get("components") if isinstance(payload, dict) else []
    return {
        "surfaceUpdate": {
            "surfaceId": spec.ui_id,
            "components": [_to_surface_component(item) for item in (components or [])],
        }
    }


def build_begin_rendering_message(spec: MetaUISpec, *, catalog_id: Optional[str] = None) -> Dict[str, Any]:
    root = spec.root[0] if spec.root else (spec.components[0].id if spec.components else "")
    resolved_catalog_id = catalog_id
    if not resolved_catalog_id:
        resolved_catalog_id = build_catalog_snapshot(get_component_catalog())["catalogId"]
    payload: Dict[str, Any] = {
        "surfaceId": spec.ui_id,
        "root": root,
        "catalogId": resolved_catalog_id,
        "sendDataModel": bool(spec.send_data_model),
    }
    if isinstance(spec.theme, Mapping) and spec.theme:
        payload["styles"] = {"theme": dict(spec.theme)}
    return {"beginRendering": payload}


def build_data_model_update_message(
    *,
    surface_id: str,
    state_patch: Mapping[str, Any],
    path: str = "/",
) -> Dict[str, Any]:
    return {
        "dataModelUpdate": {
            "surfaceId": str(surface_id),
            "path": str(path or "/"),
            "contents": encode_object_to_contents(state_patch),
        }
    }


def build_delete_surface_message(*, surface_id: str) -> Dict[str, Any]:
    return {"deleteSurface": {"surfaceId": str(surface_id)}}


def build_ui_render_sequence(
    *,
    spec: MetaUISpec,
    state: Optional[Mapping[str, Any]] = None,
    catalog_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    sequence: List[Dict[str, Any]] = [build_surface_update_message(spec)]
    if state:
        sequence.append(
            build_data_model_update_message(
                surface_id=spec.ui_id,
                state_patch=state,
                path="/",
            )
        )
    sequence.append(build_begin_rendering_message(spec, catalog_id=catalog_id))
    return sequence
