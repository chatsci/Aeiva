from __future__ import annotations

from typing import Any, Dict, List

from aeiva.realtime.turn_based_response_strategy import supported_turn_based_response_profiles


class ConfigValidationError(ValueError):
    """Raised when runtime configuration is structurally invalid."""


VALID_REALTIME_MODES = {"turn_based", "live"}
VALID_REALTIME_PROVIDERS = {"openai", "minicpm_local", "minicpm"}
VALID_GATEWAY_SCOPES = {"shared", "dedicated"}
VALID_SESSION_SCOPES = {"shared", "per_channel", "per_user", "per_channel_user"}
VALID_LIVE_UI_CAPABILITY_KEYS = {
    "text_input",
    "text_output",
    "audio_input",
    "audio_output",
    "video_input",
    "image_input",
    "file_input",
    "duplex",
}
FALLBACK_LLM_PROVIDERS = {"litellm", "minicpm_local", "minicpm"}
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


def _normalize_live_ui_capabilities(value: Any, *, path: str) -> Dict[str, bool]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigValidationError(f"{path} must be an object")
    normalized: Dict[str, bool] = {}
    for key, raw in value.items():
        if key not in VALID_LIVE_UI_CAPABILITY_KEYS:
            allowed_values = ", ".join(sorted(VALID_LIVE_UI_CAPABILITY_KEYS))
            raise ConfigValidationError(
                f"{path}.{key} is not supported. Supported capability keys: {allowed_values}"
            )
        if isinstance(raw, bool):
            normalized[key] = raw
            continue
        if isinstance(raw, (int, float)):
            normalized[key] = bool(raw)
            continue
        if isinstance(raw, str):
            lowered = raw.strip().lower()
            if lowered in {"1", "true", "yes", "on", "enabled"}:
                normalized[key] = True
                continue
            if lowered in {"0", "false", "no", "off", "disabled"}:
                normalized[key] = False
                continue
        raise ConfigValidationError(f"{path}.{key} must be a boolean-like value")
    return normalized


def _normalize_positive_int(value: Any, *, path: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ConfigValidationError(f"{path} must be a positive integer") from None
    if parsed <= 0:
        raise ConfigValidationError(f"{path} must be a positive integer")
    return parsed


def _known_llm_providers() -> set[str]:
    try:
        from aeiva.llm.providers.registry import get_registered_provider_names

        providers = set(get_registered_provider_names(include_aliases=True))
        if providers:
            return providers
    except Exception:
        pass
    return set(FALLBACK_LLM_PROVIDERS)


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

    if "ui_capabilities" in realtime_cfg:
        realtime_cfg["ui_capabilities"] = _normalize_live_ui_capabilities(
            realtime_cfg.get("ui_capabilities"),
            path="realtime_config.ui_capabilities",
        )

    for provider_key in ("openai", "minicpm", "turn_based"):
        provider_cfg = realtime_cfg.get(provider_key)
        if provider_cfg is None:
            continue
        if not isinstance(provider_cfg, dict):
            raise ConfigValidationError(f"realtime_config.{provider_key} must be an object")
        if provider_key == "turn_based" and "response_profile" in provider_cfg:
            response_profile = provider_cfg.get("response_profile")
            if not isinstance(response_profile, str):
                raise ConfigValidationError(
                    "realtime_config.turn_based.response_profile must be a string"
                )
            provider_cfg["response_profile"] = response_profile.strip().lower()
        if "ui_capabilities" in provider_cfg:
            provider_cfg["ui_capabilities"] = _normalize_live_ui_capabilities(
                provider_cfg.get("ui_capabilities"),
                path=f"realtime_config.{provider_key}.ui_capabilities",
            )

    config_dict["realtime_config"] = realtime_cfg


def normalize_event_config(config_dict: Dict[str, Any]) -> None:
    event_cfg = _as_dict(config_dict.get("event_config"))
    if not event_cfg:
        return

    int_fields = (
        "lane_queue_limit",
        "readonly_concurrency",
        "max_hop_count",
        "max_history",
    )
    for field in int_fields:
        if field not in event_cfg:
            continue
        event_cfg[field] = _normalize_positive_int(event_cfg.get(field), path=f"event_config.{field}")

    config_dict["event_config"] = event_cfg


def normalize_llm_config(config_dict: Dict[str, Any]) -> None:
    llm_cfg = _as_dict(config_dict.get("llm_gateway_config"))
    if not llm_cfg:
        return

    provider = llm_cfg.get("llm_provider", "litellm")
    if not isinstance(provider, str):
        raise ConfigValidationError("llm_gateway_config.llm_provider must be a string")
    normalized_provider = provider.strip().lower() or "litellm"
    llm_cfg["llm_provider"] = normalized_provider

    provider_cfg = llm_cfg.get("llm_provider_config", {})
    if provider_cfg is None:
        provider_cfg = {}
    if not isinstance(provider_cfg, dict):
        raise ConfigValidationError("llm_gateway_config.llm_provider_config must be an object")
    llm_cfg["llm_provider_config"] = provider_cfg

    config_dict["llm_gateway_config"] = llm_cfg


def normalize_runtime_config(config_dict: Dict[str, Any]) -> None:
    normalize_action_tools(config_dict)
    normalize_realtime_config(config_dict)
    normalize_event_config(config_dict)
    normalize_llm_config(config_dict)


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
        if provider == "openai":
            openai_cfg = _as_dict(realtime_cfg.get("openai"))
            model_name = openai_cfg.get("model", "")
            if not isinstance(model_name, str) or not model_name.strip():
                raise ConfigValidationError(
                    "realtime_config.openai.model must be a non-empty string in live mode"
                )
            return

        minicpm_cfg = _as_dict(realtime_cfg.get("minicpm"))
        transport = str(minicpm_cfg.get("transport", "omni_http")).strip().lower()
        if transport not in {"omni_http", "openai_realtime_compat"}:
            raise ConfigValidationError(
                "realtime_config.minicpm.transport must be 'omni_http' "
                "(or legacy 'openai_realtime_compat')"
            )
        base_url = minicpm_cfg.get("base_url")
        if base_url is not None and (not isinstance(base_url, str) or not base_url.strip()):
            raise ConfigValidationError("realtime_config.minicpm.base_url must be a non-empty string")
        if isinstance(base_url, str) and base_url.strip():
            normalized_base_url = base_url.strip().lower()
            if transport == "omni_http" and not normalized_base_url.startswith(("http://", "https://")):
                raise ConfigValidationError(
                    "realtime_config.minicpm.base_url must start with http:// or https:// "
                    "when transport='omni_http'"
                )
        if "init_retries" in minicpm_cfg:
            _normalize_positive_int(
                minicpm_cfg.get("init_retries"),
                path="realtime_config.minicpm.init_retries",
            )
        if "init_retry_backoff_seconds" in minicpm_cfg:
            try:
                backoff = float(minicpm_cfg.get("init_retry_backoff_seconds"))
            except Exception as exc:
                raise ConfigValidationError(
                    "realtime_config.minicpm.init_retry_backoff_seconds must be a number"
                ) from exc
            if backoff < 0:
                raise ConfigValidationError(
                    "realtime_config.minicpm.init_retry_backoff_seconds must be >= 0"
                )
        if "text_fallback_retries" in minicpm_cfg:
            _normalize_positive_int(
                minicpm_cfg.get("text_fallback_retries"),
                path="realtime_config.minicpm.text_fallback_retries",
            )
        if "text_fallback_retry_backoff_seconds" in minicpm_cfg:
            try:
                text_backoff = float(minicpm_cfg.get("text_fallback_retry_backoff_seconds"))
            except Exception as exc:
                raise ConfigValidationError(
                    "realtime_config.minicpm.text_fallback_retry_backoff_seconds must be a number"
                ) from exc
            if text_backoff < 0:
                raise ConfigValidationError(
                    "realtime_config.minicpm.text_fallback_retry_backoff_seconds must be >= 0"
                )
        return

    # turn_based mode
    turn_based_cfg = _as_dict(realtime_cfg.get("turn_based"))
    response_profile = turn_based_cfg.get("response_profile")
    if response_profile is not None:
        if not isinstance(response_profile, str) or not response_profile.strip():
            raise ConfigValidationError(
                "realtime_config.turn_based.response_profile must be a non-empty string"
            )
        normalized_profile = response_profile.strip().lower()
        supported_profiles = supported_turn_based_response_profiles()
        if normalized_profile not in supported_profiles:
            supported = ", ".join(supported_profiles)
            raise ConfigValidationError(
                "realtime_config.turn_based.response_profile must be one of: "
                f"{supported}"
            )
    stt_cfg = _as_dict(realtime_cfg.get("stt"))
    tts_cfg = _as_dict(realtime_cfg.get("tts"))
    for path, cfg in (("realtime_config.stt", stt_cfg), ("realtime_config.tts", tts_cfg)):
        backend = cfg.get("backend")
        if backend is not None and not isinstance(backend, str):
            raise ConfigValidationError(f"{path}.backend must be a string when provided")


def validate_event_config(config_dict: Dict[str, Any]) -> None:
    event_cfg = _as_dict(config_dict.get("event_config"))
    if not event_cfg:
        return
    # normalized in normalize_event_config; this pass keeps error path explicit
    for field in ("lane_queue_limit", "readonly_concurrency", "max_hop_count", "max_history"):
        if field in event_cfg:
            _normalize_positive_int(event_cfg.get(field), path=f"event_config.{field}")


def validate_llm_config(config_dict: Dict[str, Any]) -> None:
    llm_cfg = _as_dict(config_dict.get("llm_gateway_config"))
    if not llm_cfg:
        return

    provider = str(llm_cfg.get("llm_provider", "litellm")).strip().lower()
    supported = _known_llm_providers()
    if provider not in supported:
        allowed = ", ".join(sorted(supported))
        raise ConfigValidationError(
            f"llm_gateway_config.llm_provider='{provider}' is not supported. Supported providers: {allowed}"
        )

    provider_cfg = llm_cfg.get("llm_provider_config")
    if provider_cfg is not None and not isinstance(provider_cfg, dict):
        raise ConfigValidationError("llm_gateway_config.llm_provider_config must be an object")


def validate_runtime_config(config_dict: Dict[str, Any]) -> None:
    """Run runtime config normalization followed by validations."""
    normalize_runtime_config(config_dict)
    validate_action_tools(config_dict)
    validate_realtime_config(config_dict)
    validate_event_config(config_dict)
    validate_llm_config(config_dict)
