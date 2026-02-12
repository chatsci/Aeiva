from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

from .a2ui_runtime import evaluate_check_definitions
from .protocol import MetaUIEvent, MetaUISpec
from .upload_store import UploadStore


def sanitize_event_payload(
    payload: Mapping[str, Any],
    *,
    max_depth: int = 8,
    max_list_items: int = 64,
    max_text_chars: int = 4000,
) -> Dict[str, Any]:
    """
    Return a model-safe event payload.

    Goals:
    - redact binary/base64 blobs to avoid huge prompt payloads
    - bound nested structures to keep event history predictable
    - preserve user-meaningful metadata (paths, names, values)
    """

    redacted_tokens = {
        "content_base64",
        "base64",
        "data_base64",
        "binary",
        "bytes",
        "blob",
        "arraybuffer",
    }

    def _walk(value: Any, depth: int) -> Any:
        if depth >= max_depth:
            return "<truncated_depth>"
        if isinstance(value, Mapping):
            out: Dict[str, Any] = {}
            for raw_key, raw_item in value.items():
                key = str(raw_key)
                token = key.strip().lower()
                if token in redacted_tokens:
                    if isinstance(raw_item, str):
                        out[key] = f"<redacted:{len(raw_item)} chars>"
                    else:
                        out[key] = "<redacted>"
                    continue
                out[key] = _walk(raw_item, depth + 1)
            return out
        if isinstance(value, list):
            items = [_walk(item, depth + 1) for item in value[:max_list_items]]
            overflow = len(value) - len(items)
            if overflow > 0:
                items.append({"_truncated_items": overflow})
            return items
        if isinstance(value, str):
            if len(value) <= max_text_chars:
                return value
            return value[:max_text_chars] + "...<truncated>"
        return value

    return _walk(dict(payload), 0)


def translate_client_event_message(message: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """Translate A2UI-style client envelopes into the internal MetaUI event schema."""

    action_payload = message.get("action")
    if isinstance(action_payload, Mapping):
        ui_id = str(action_payload.get("surfaceId") or message.get("ui_id") or "").strip()
        if not ui_id:
            return None
        component_id = str(
            action_payload.get("sourceComponentId") or message.get("component_id") or ""
        ).strip()
        event_type = str(action_payload.get("name") or message.get("event_type") or "action").strip()
        context = action_payload.get("context")
        payload: Dict[str, Any] = deepcopy(dict(context)) if isinstance(context, Mapping) else {}
        metadata: Dict[str, Any] = {
            "source": "a2ui_client",
            "a2ui_version": str(message.get("version") or "").strip() or None,
            "timestamp": str(action_payload.get("timestamp") or "").strip() or None,
        }
        return {
            "ui_id": ui_id,
            "session_id": message.get("session_id"),
            "component_id": component_id or None,
            "event_type": event_type or "action",
            "payload": payload,
            "metadata": metadata,
        }

    error_payload = message.get("error")
    if isinstance(error_payload, Mapping):
        ui_id = str(error_payload.get("surfaceId") or message.get("ui_id") or "").strip()
        if not ui_id:
            return None
        payload = deepcopy(dict(error_payload))
        metadata: Dict[str, Any] = {
            "source": "a2ui_client",
            "a2ui_version": str(message.get("version") or "").strip() or None,
        }
        return {
            "ui_id": ui_id,
            "session_id": message.get("session_id"),
            "component_id": None,
            "event_type": "error",
            "payload": payload,
            "metadata": metadata,
        }

    return None


def persist_event_uploads(event: MetaUIEvent, *, upload_store: UploadStore) -> None:
    if event.event_type != "upload":
        return
    session_id = event.session_id or "default"
    files = event.payload.get("files")
    upload_result = upload_store.persist_files(
        files=files if isinstance(files, list) else [],
        session_id=session_id,
        event_id=event.event_id,
    )
    event.payload = dict(event.payload)
    event.payload["upload_result"] = upload_result


def sanitize_event_payload_in_place(event: MetaUIEvent) -> None:
    if isinstance(event.payload, Mapping):
        event.payload = sanitize_event_payload(event.payload)


def event_validation_errors(
    *,
    event: MetaUIEvent,
    validation_component: Optional[Mapping[str, Any]],
    validation_state: Mapping[str, Any],
) -> list[str]:
    if validation_component is None:
        return []
    payload = event.payload if isinstance(event.payload, Mapping) else {}
    return _validate_event_checks_for_component(
        component=validation_component,
        payload=payload,
        state=validation_state,
    )


def _find_component_by_id(spec: MetaUISpec, component_id: str) -> Mapping[str, Any] | None:
    target = str(component_id or "").strip()
    if not target:
        return None
    for component in spec.components:
        if component.id == target:
            return component.model_dump(mode="json")
    return None


def find_validation_component(
    *,
    spec: MetaUISpec,
    component_id: str,
) -> Optional[Mapping[str, Any]]:
    component = _find_component_by_id(spec, component_id)
    if component is None:
        return None
    return deepcopy(dict(component))


def _validate_input_component_checks(
    *,
    component_props: Mapping[str, Any],
    payload: Mapping[str, Any],
    state: Mapping[str, Any],
) -> list[str]:
    checks = component_props.get("checks")
    if not isinstance(checks, list) or not checks:
        return []
    value = payload.get("value")
    if value is None and "checked" in payload:
        value = payload.get("checked")
    context = {
        "payload": dict(payload),
        "form_values": dict(payload.get("values") or {}) if isinstance(payload.get("values"), Mapping) else {},
    }
    return evaluate_check_definitions(
        checks=checks,
        data_model=state,
        default_value=value,
        context=context,
    )


def _validate_event_checks_for_component(
    *,
    component: Mapping[str, Any],
    payload: Mapping[str, Any],
    state: Mapping[str, Any],
) -> list[str]:
    component_type = str(component.get("type") or "")
    props = component.get("props")
    if not isinstance(props, Mapping):
        return []
    if component_type in {"TextField", "CheckBox", "ChoicePicker", "Slider", "DateTimeInput"}:
        return _validate_input_component_checks(
            component_props=props,
            payload=payload,
            state=state,
        )
    return []
