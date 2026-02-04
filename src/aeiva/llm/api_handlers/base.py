"""
Base protocol for LLM API handlers.

Defines the interface that all API handlers must implement.
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple

from aeiva.llm.llm_gateway_config import LLMGatewayConfig


class LLMHandler(Protocol):
    """
    Protocol defining the interface for LLM API handlers.

    Each handler manages a specific API format (chat/completions or responses).
    """

    config: LLMGatewayConfig

    def build_params(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Build API request parameters."""
        ...

    def parse_response(
        self,
        response: Any,
    ) -> Tuple[Optional[Any], List[Any], str]:
        """
        Parse API response.

        Returns:
            Tuple of (message_object, tool_calls, content_text)
        """
        ...

    def parse_stream_delta(
        self,
        chunk: Any,
        **kwargs,
    ) -> Tuple[Optional[str], Optional[List[Any]]]:
        """
        Parse streaming chunk.

        Returns:
            Tuple of (content_delta, tool_call_deltas)
        """
        ...

    async def execute(
        self,
        params: Dict[str, Any],
        stream: bool = False,
    ) -> Any:
        """Execute API call (streaming or non-streaming)."""
        ...

    def execute_sync(
        self,
        params: Dict[str, Any],
    ) -> Any:
        """Execute API call synchronously."""
        ...


class BaseHandler:
    """
    Base implementation with shared utilities for all handlers.
    """

    def __init__(self, config: LLMGatewayConfig):
        self.config = config
        self._unsupported_params: Dict[str, set] = {}

    def _add_auth_params(self, params: Dict[str, Any]) -> None:
        """Add authentication and base URL parameters."""
        if self.config.llm_api_key:
            params["api_key"] = self.config.llm_api_key
        if self.config.llm_base_url:
            params["base_url"] = self.config.llm_base_url
        if self.config.llm_api_version:
            params["api_version"] = self.config.llm_api_version
        if self.config.llm_custom_provider:
            params["custom_llm_provider"] = self.config.llm_custom_provider

    def _add_additional_params(self, params: Dict[str, Any], **kwargs) -> None:
        """Merge additional parameters from config and kwargs."""
        if self.config.llm_additional_params:
            params.update(self.config.llm_additional_params)
        params.update(kwargs)

    def _strip_unsupported_params(self, params: Dict[str, Any]) -> None:
        """Remove parameters that are known to be unsupported for this model."""
        model_name = params.get("model")
        if not model_name:
            return
        blocked = self._unsupported_params.get(model_name)
        if blocked:
            for key in list(blocked):
                params.pop(key, None)

    def _handle_unsupported_param_error(
        self,
        params: Dict[str, Any],
        error: Exception,
    ) -> bool:
        """
        Try to extract and remove unsupported parameter from error message.

        Returns:
            True if a parameter was removed and retry should be attempted.
        """
        import re

        message = str(error)
        patterns = [
            r"Unsupported parameter: ['\"]([^'\"]+)['\"]",
            r"parameter ['\"]([^'\"]+)['\"] is not supported",
            r"['\"]([^'\"]+)['\"] is not supported with this model",
            r"does not support (?:the )?parameter ['\"]([^'\"]+)['\"]",
            r"does not support (?:the )?parameters?:\s*([a-zA-Z0-9_]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                param = match.group(1)
                # Handle aliases
                alias_map = {
                    "max_tokens": "max_output_tokens",
                    "max_completion_tokens": "max_output_tokens",
                    "text.format": "text",
                }

                if param in params:
                    params.pop(param, None)
                    model_name = params.get("model")
                    if model_name:
                        self._unsupported_params.setdefault(model_name, set()).add(param)
                    return True

                alias = alias_map.get(param)
                if alias and alias in params:
                    params.pop(alias, None)
                    model_name = params.get("model")
                    if model_name:
                        self._unsupported_params.setdefault(model_name, set()).add(alias)
                    return True

        return False

    async def _execute_with_fallback(
        self,
        call_fn,
        params: Dict[str, Any],
        max_retries: int = 3,
    ) -> Any:
        """Execute with automatic parameter fallback on unsupported param errors."""
        self._strip_unsupported_params(params)

        for _ in range(max_retries):
            try:
                return await call_fn(**params)
            except Exception as error:
                if self._handle_unsupported_param_error(params, error):
                    continue
                raise

        # Final attempt
        return await call_fn(**params)

    def _execute_with_fallback_sync(
        self,
        call_fn,
        params: Dict[str, Any],
        max_retries: int = 3,
    ) -> Any:
        """Execute synchronously with automatic parameter fallback."""
        self._strip_unsupported_params(params)

        for _ in range(max_retries):
            try:
                return call_fn(**params)
            except Exception as error:
                if self._handle_unsupported_param_error(params, error):
                    continue
                raise

        return call_fn(**params)
