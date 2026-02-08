from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Tuple


SUPPORTED_PROTOCOL_VERSIONS: Tuple[str, ...] = ("1.0",)
SUPPORTED_FEATURES: Tuple[str, ...] = (
    "a2ui_stream_v1",
    "json_pointer_bindings_v1",
)


def _clean_string_items(values: Iterable[Any]) -> Tuple[str, ...]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


@dataclass(frozen=True)
class MetaUIClientCapabilities:
    protocol_version: str
    supported_components: Tuple[str, ...]
    supported_commands: Tuple[str, ...]
    features: Tuple[str, ...]
    raw_hello: Dict[str, Any]

    def supports_feature(self, feature: str) -> bool:
        return str(feature or "").strip() in self.features

    def supports_component(self, component_type: str) -> bool:
        return str(component_type or "").strip() in self.supported_components


def build_catalog_snapshot(server_catalog: Dict[str, Any]) -> Dict[str, Any]:
    catalog = server_catalog if isinstance(server_catalog, dict) else {}
    version = str(catalog.get("version") or "1.0")
    components = catalog.get("components")
    component_types = sorted(components.keys()) if isinstance(components, dict) else []
    return {
        "catalogId": f"aeiva://metaui/catalog/{version}",
        "version": version,
        "componentTypes": component_types,
    }


def negotiate_client_capabilities(
    *,
    hello_payload: Dict[str, Any],
    server_catalog: Dict[str, Any],
) -> MetaUIClientCapabilities:
    hello = hello_payload if isinstance(hello_payload, dict) else {}

    requested_versions = _clean_string_items(hello.get("protocol_versions") or ())
    protocol_version = SUPPORTED_PROTOCOL_VERSIONS[0]
    if requested_versions:
        for candidate in requested_versions:
            if candidate in SUPPORTED_PROTOCOL_VERSIONS:
                protocol_version = candidate
                break

    server_component_types = set(build_catalog_snapshot(server_catalog)["componentTypes"])
    requested_components = _clean_string_items(hello.get("supported_components") or ())
    if requested_components:
        supported_components = tuple(
            sorted(component for component in requested_components if component in server_component_types)
        )
    else:
        supported_components = tuple(sorted(server_component_types))

    requested_commands = _clean_string_items(hello.get("supported_commands") or ())
    requested_features = _clean_string_items(hello.get("features") or ())
    negotiated_features = tuple(feature for feature in requested_features if feature in SUPPORTED_FEATURES)

    return MetaUIClientCapabilities(
        protocol_version=protocol_version,
        supported_components=supported_components,
        supported_commands=requested_commands,
        features=negotiated_features,
        raw_hello=dict(hello),
    )
