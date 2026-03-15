from __future__ import annotations

from dataclasses import replace
import json
import os
from typing import Any, Dict, Optional
from urllib.error import URLError
from urllib.request import urlopen

from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.llm.providers.litellm_provider import LiteLLMProvider


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
            continue
        if value is not None:
            return value
    return None


class MiniCPMLocalProvider(LiteLLMProvider):
    """
    MiniCPM local provider profile.

    It still uses the LiteLLM-compatible gateway path, but injects local-first
    defaults so AEIVA can run without remote API dependencies.
    """

    provider_name = "minicpm_local"
    requires_api_key = False

    # WebRTC_Demo exposes OpenAI-compatible chat routes on llama-server port 19060.
    DEFAULT_BASE_URL = "http://127.0.0.1:19060/v1"
    DEFAULT_MODEL = "openbmb/MiniCPM-o-4_5"
    DEFAULT_API_KEY = "local-placeholder"

    def __init__(self, config: LLMGatewayConfig):
        self.source_config = config
        effective_config = self._build_effective_config(config)
        self.effective_config = effective_config
        self._resolved_model_id: Optional[str] = None
        super().__init__(effective_config)
        self._register_model_cost_hint(effective_config.llm_model_name)

    def _build_effective_config(self, config: LLMGatewayConfig) -> LLMGatewayConfig:
        provider_cfg = config.llm_provider_config or {}
        if not isinstance(provider_cfg, dict):
            provider_cfg = {}

        additional_params: Dict[str, Any] = dict(config.llm_additional_params or {})
        provider_additional = provider_cfg.get("additional_params")
        if isinstance(provider_additional, dict):
            additional_params.update(provider_additional)

        model_name = _first_non_empty(
            provider_cfg.get("model"),
            config.llm_model_name,
            self.DEFAULT_MODEL,
        )
        base_url = _first_non_empty(
            provider_cfg.get("base_url"),
            config.llm_base_url,
            self.DEFAULT_BASE_URL,
        )
        api_key = _first_non_empty(
            provider_cfg.get("api_key"),
            config.llm_api_key,
            self.DEFAULT_API_KEY,
        )
        custom_provider = _first_non_empty(
            provider_cfg.get("custom_provider"),
            config.llm_custom_provider,
            "openai",
        )
        raw_api_mode = _first_non_empty(provider_cfg.get("api_mode"), config.llm_api_mode)
        api_mode = str(raw_api_mode).strip().lower() if raw_api_mode is not None else "chat"
        if not api_mode or api_mode == "auto":
            api_mode = "chat"

        return replace(
            config,
            llm_provider=self.provider_name,
            llm_model_name=model_name,
            llm_base_url=base_url,
            llm_api_key=api_key,
            llm_custom_provider=custom_provider,
            llm_api_mode=api_mode,
            llm_timeout=provider_cfg.get("timeout", config.llm_timeout),
            llm_temperature=provider_cfg.get("temperature", config.llm_temperature),
            llm_top_p=provider_cfg.get("top_p", config.llm_top_p),
            llm_max_output_tokens=provider_cfg.get(
                "max_output_tokens",
                config.llm_max_output_tokens,
            ),
            llm_additional_params=additional_params,
        )

    def build_params(self, messages, tools=None, **kwargs):
        params = super().build_params(messages, tools=tools, **kwargs)
        provider_cfg = self.effective_config.llm_provider_config or {}
        if isinstance(provider_cfg, dict) and provider_cfg.get("resolve_model_id", True):
            params["model"] = self._normalize_model_id(params.get("model"))
        return params

    def _normalize_model_id(self, model_name: Any) -> Any:
        if not isinstance(model_name, str) or not model_name.strip():
            return model_name
        if os.path.isabs(model_name):
            return model_name
        resolved = self._resolve_first_model_id()
        return resolved or model_name

    def _resolve_first_model_id(self) -> Optional[str]:
        if self._resolved_model_id:
            return self._resolved_model_id

        base_url = str(self.effective_config.llm_base_url or "").strip().rstrip("/")
        if not base_url:
            return None
        models_url = f"{base_url}/models" if base_url.endswith("/v1") else f"{base_url}/v1/models"

        try:
            with urlopen(models_url, timeout=1.5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
            return None

        candidates = payload.get("data") or payload.get("models") or []
        if not isinstance(candidates, list) or not candidates:
            return None
        first = candidates[0] if isinstance(candidates[0], dict) else {}
        model_id = first.get("id") or first.get("model") or first.get("name")
        if isinstance(model_id, str) and model_id.strip():
            self._resolved_model_id = model_id.strip()
            self._register_model_cost_hint(self._resolved_model_id)
            return self._resolved_model_id
        return None

    def _register_model_cost_hint(self, model_id: Optional[str]) -> None:
        """
        Register a zero-cost model hint in LiteLLM for local MiniCPM endpoints.

        This prevents noisy "model isn't mapped yet" warnings during response-cost
        calculation when model ids are local file paths.
        """
        if not isinstance(model_id, str) or not model_id.strip():
            return
        try:
            import litellm
        except Exception:
            return

        model_id = model_id.strip()
        model_cost = getattr(litellm, "model_cost", None)
        if not isinstance(model_cost, dict):
            return

        template = {
            "litellm_provider": "openai",
            "mode": "chat",
            "input_cost_per_token": 0.0,
            "output_cost_per_token": 0.0,
            "max_tokens": 8192,
            "max_input_tokens": 8192,
            "max_output_tokens": 4096,
            "supports_system_messages": True,
            "supports_function_calling": True,
            "supports_tool_choice": True,
        }

        keys = {model_id}
        if not model_id.startswith("openai/"):
            keys.add(f"openai/{model_id}")

        for key in keys:
            existing = model_cost.get(key)
            if isinstance(existing, dict):
                existing.setdefault("litellm_provider", "openai")
                existing.setdefault("mode", "chat")
                existing.setdefault("input_cost_per_token", 0.0)
                existing.setdefault("output_cost_per_token", 0.0)
                existing.setdefault("max_tokens", 8192)
                continue
            model_cost[key] = dict(template)
