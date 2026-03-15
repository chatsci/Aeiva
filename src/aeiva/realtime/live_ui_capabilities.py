from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping


_CAPABILITY_KEYS = (
    "text_input",
    "text_output",
    "audio_input",
    "audio_output",
    "video_input",
    "image_input",
    "file_input",
    "duplex",
)


@dataclass(frozen=True)
class LiveUICapabilities:
    """
    Capability profile that drives the unified multimodal realtime UI.

    UI widgets and event wiring should be derived from this profile so providers
    stay transport-focused and UI logic remains clean and provider-agnostic.
    """

    text_input: bool = True
    text_output: bool = True
    audio_input: bool = True
    audio_output: bool = True
    video_input: bool = True
    image_input: bool = True
    file_input: bool = False
    duplex: bool = True

    def enabled_inputs(self) -> list[str]:
        labels: list[str] = []
        if self.text_input:
            labels.append("text")
        if self.audio_input:
            labels.append("audio")
        if self.video_input:
            labels.append("video")
        if self.image_input:
            labels.append("image")
        if self.file_input:
            labels.append("file")
        return labels


def _normalize_override_value(value: Any, *, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on", "enabled"}:
            return True
        if lowered in {"0", "false", "no", "off", "disabled"}:
            return False
    return fallback


def apply_capability_overrides(
    base: LiveUICapabilities,
    overrides: Mapping[str, Any] | None,
) -> LiveUICapabilities:
    if not isinstance(overrides, Mapping):
        return base
    updated = base
    for key in _CAPABILITY_KEYS:
        if key not in overrides:
            continue
        current = getattr(updated, key)
        normalized = _normalize_override_value(overrides.get(key), fallback=current)
        updated = replace(updated, **{key: normalized})
    return updated


def resolve_live_ui_capabilities(
    *,
    realtime_cfg: Mapping[str, Any] | None,
    provider_cfg: Mapping[str, Any] | None = None,
    defaults: LiveUICapabilities | None = None,
) -> LiveUICapabilities:
    """
    Resolve final capability profile using:
    1) provider defaults
    2) global realtime_config.ui_capabilities overrides
    3) provider-specific ui_capabilities overrides
    """

    resolved = defaults or LiveUICapabilities()
    if isinstance(realtime_cfg, Mapping):
        resolved = apply_capability_overrides(
            resolved,
            realtime_cfg.get("ui_capabilities"),
        )
    if isinstance(provider_cfg, Mapping):
        resolved = apply_capability_overrides(
            resolved,
            provider_cfg.get("ui_capabilities"),
        )
    return resolved

