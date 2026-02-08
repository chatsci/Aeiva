from __future__ import annotations

from typing import Any, Dict, List


class ConfigValidationError(ValueError):
    """Raised when runtime configuration is structurally invalid."""


VALID_REALTIME_MODES = {"turn_based", "live"}
VALID_REALTIME_PROVIDERS = {"openai"}
VALID_GATEWAY_SCOPES = {"shared", "dedicated"}
VALID_SESSION_SCOPES = {"shared", "per_channel", "per_user", "per_channel_user"}
_LEGACY_TOOL_ALIASES = {
    "read_file": "filesystem",
    "write_file": "filesystem",
    "list_directory": "filesystem",
    "delete_file": "filesystem",
    "http_request": "browser",
    "browser_action": "browser",
    "code_execute": "shell",
    "git": "shell",
    "git_clone": "shell",
}


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_string_list(values: Any, *, path: str) -> List[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ConfigValidationError(f"{path} must be a list of strings")
    normalized: List[str] = []
    for index, item in enumerate(values):
        if not isinstance(item, str):
            raise ConfigValidationError(f"{path}[{index}] must be a string")
        value = item.strip()
        if not value:
            raise ConfigValidationError(f"{path}[{index}] cannot be empty")
        normalized.append(value)
    return normalized


def _normalize_scope(
    value: Any,
    *,
    path: str,
    allowed: set[str],
) -> str:
    if not isinstance(value, str):
        raise ConfigValidationError(f"{path} must be a string")
    normalized = value.strip().lower()
    if normalized not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ConfigValidationError(f"{path} must be one of: {allowed_values}")
    return normalized


def normalize_action_tools(config_dict: Dict[str, Any]) -> None:
    action_cfg = _as_dict(config_dict.get("action_config"))
    raw_tools = action_cfg.get("tools")
    if raw_tools is None:
        return

    tools = _normalize_string_list(raw_tools, path="action_config.tools")
    normalized_tools: List[str] = []
    seen: set[str] = set()
    for tool_name in tools:
        canonical_name = _LEGACY_TOOL_ALIASES.get(tool_name, tool_name)
        if canonical_name in seen:
            continue
        normalized_tools.append(canonical_name)
        seen.add(canonical_name)

    action_cfg["tools"] = normalized_tools
    config_dict["action_config"] = action_cfg


def normalize_realtime_config(config_dict: Dict[str, Any]) -> None:
    realtime_cfg = _as_dict(config_dict.get("realtime_config"))
    if not realtime_cfg:
        return

    mode = realtime_cfg.get("mode", "turn_based")
    if not isinstance(mode, str):
        raise ConfigValidationError("realtime_config.mode must be a string")
    realtime_cfg["mode"] = mode.strip().lower()

    provider = realtime_cfg.get("provider", "openai")
    if not isinstance(provider, str):
        raise ConfigValidationError("realtime_config.provider must be a string")
    realtime_cfg["provider"] = provider.strip().lower()

    gateway_cfg = _as_dict(config_dict.get("gateway_config"))
    default_scope = gateway_cfg.get("default_scope", "shared")
    default_session_scope = gateway_cfg.get("default_session_scope", "shared")

    if "gateway_scope" in realtime_cfg:
        gateway_scope = realtime_cfg["gateway_scope"]
    else:
        gateway_scope = default_scope
    realtime_cfg["gateway_scope"] = _normalize_scope(
        gateway_scope,
        path="realtime_config.gateway_scope",
        allowed=VALID_GATEWAY_SCOPES,
    )

    if "session_scope" in realtime_cfg:
        session_scope = realtime_cfg["session_scope"]
    else:
        session_scope = default_session_scope
    realtime_cfg["session_scope"] = _normalize_scope(
        session_scope,
        path="realtime_config.session_scope",
        allowed=VALID_SESSION_SCOPES,
    )

    for path in ("stt", "tts"):
        cfg = realtime_cfg.get(path)
        if cfg is None:
            continue
        if not isinstance(cfg, dict):
            raise ConfigValidationError(f"realtime_config.{path} must be an object")
        backend = cfg.get("backend")
        if backend is not None:
            if not isinstance(backend, str):
                raise ConfigValidationError(f"realtime_config.{path}.backend must be a string")
            cfg["backend"] = backend.strip().lower()

    config_dict["realtime_config"] = realtime_cfg


def normalize_runtime_config(config_dict: Dict[str, Any]) -> None:
    normalize_action_tools(config_dict)
    normalize_realtime_config(config_dict)
    normalize_metaui_config(config_dict)


def _as_positive_int(value: Any, *, path: str) -> int:
    if not isinstance(value, int):
        raise ConfigValidationError(f"{path} must be an integer")
    if value <= 0:
        raise ConfigValidationError(f"{path} must be > 0")
    return value


def normalize_metaui_config(config_dict: Dict[str, Any]) -> None:
    metaui_cfg = _as_dict(config_dict.get("metaui_config"))
    if not metaui_cfg:
        return

    enabled = metaui_cfg.get("enabled")
    if enabled is not None:
        metaui_cfg["enabled"] = bool(enabled)

    for key in ("auto_ui", "auto_start_desktop"):
        if key in metaui_cfg and metaui_cfg[key] is not None:
            metaui_cfg[key] = bool(metaui_cfg[key])

    host = metaui_cfg.get("host")
    if host is not None:
        if not isinstance(host, str) or not host.strip():
            raise ConfigValidationError("metaui_config.host must be a non-empty string")
        metaui_cfg["host"] = host.strip()

    for key in (
        "port",
        "upload_max_file_bytes",
        "upload_max_total_bytes",
        "upload_max_files_per_event",
        "event_history_limit",
    ):
        if key in metaui_cfg:
            metaui_cfg[key] = _as_positive_int(metaui_cfg[key], path=f"metaui_config.{key}")

    for key in ("hello_timeout_seconds", "send_timeout_seconds", "wait_ack_seconds"):
        if key in metaui_cfg:
            try:
                value = float(metaui_cfg[key])
            except Exception as exc:
                raise ConfigValidationError(f"metaui_config.{key} must be a number") from exc
            if value < 0:
                raise ConfigValidationError(f"metaui_config.{key} must be >= 0")
            metaui_cfg[key] = value

    for key in ("token", "token_env_var", "upload_base_dir", "desktop_log_file"):
        if key in metaui_cfg and metaui_cfg[key] is not None:
            value = metaui_cfg[key]
            if not isinstance(value, str) or not value.strip():
                raise ConfigValidationError(f"metaui_config.{key} must be a non-empty string")
            metaui_cfg[key] = value.strip()

    config_dict["metaui_config"] = metaui_cfg


def validate_action_tools(config_dict: Dict[str, Any]) -> None:
    """Validate that configured action tools exist in the ToolRegistry."""
    action_cfg = _as_dict(config_dict.get("action_config"))
    tool_names = _normalize_string_list(action_cfg.get("tools"), path="action_config.tools")
    if not tool_names:
        return

    from aeiva.tool.registry import get_registry

    registry = get_registry()
    available = set(registry.tool_names)
    unknown = sorted({name for name in tool_names if name not in available})
    if not unknown:
        return

    available_sorted = ", ".join(sorted(available))
    unknown_joined = ", ".join(unknown)
    raise ConfigValidationError(
        "Unknown tools in action_config.tools: "
        f"{unknown_joined}. Available tools: {available_sorted}"
    )


def validate_realtime_config(config_dict: Dict[str, Any]) -> None:
    """Validate realtime mode/provider and basic structure."""
    realtime_cfg = _as_dict(config_dict.get("realtime_config"))
    if not realtime_cfg or not bool(realtime_cfg.get("enabled", False)):
        return

    mode = str(realtime_cfg.get("mode", "turn_based")).strip().lower()
    if mode not in VALID_REALTIME_MODES:
        allowed = ", ".join(sorted(VALID_REALTIME_MODES))
        raise ConfigValidationError(f"realtime_config.mode must be one of: {allowed}")

    _normalize_scope(
        realtime_cfg.get("gateway_scope", "shared"),
        path="realtime_config.gateway_scope",
        allowed=VALID_GATEWAY_SCOPES,
    )
    _normalize_scope(
        realtime_cfg.get("session_scope", "shared"),
        path="realtime_config.session_scope",
        allowed=VALID_SESSION_SCOPES,
    )

    if mode == "live":
        provider = str(realtime_cfg.get("provider", "openai")).strip().lower()
        if provider not in VALID_REALTIME_PROVIDERS:
            allowed = ", ".join(sorted(VALID_REALTIME_PROVIDERS))
            raise ConfigValidationError(
                f"realtime_config.provider='{provider}' is not supported for live mode. "
                f"Supported providers: {allowed}"
            )
        openai_cfg = _as_dict(realtime_cfg.get("openai"))
        model_name = openai_cfg.get("model", "")
        if not isinstance(model_name, str) or not model_name.strip():
            raise ConfigValidationError(
                "realtime_config.openai.model must be a non-empty string in live mode"
            )
        return

    # turn_based mode
    stt_cfg = _as_dict(realtime_cfg.get("stt"))
    tts_cfg = _as_dict(realtime_cfg.get("tts"))
    for path, cfg in (("realtime_config.stt", stt_cfg), ("realtime_config.tts", tts_cfg)):
        backend = cfg.get("backend")
        if backend is not None and not isinstance(backend, str):
            raise ConfigValidationError(f"{path}.backend must be a string when provided")


def validate_runtime_config(config_dict: Dict[str, Any]) -> None:
    """Run runtime config normalization followed by validations."""
    normalize_runtime_config(config_dict)
    validate_action_tools(config_dict)
    validate_realtime_config(config_dict)
