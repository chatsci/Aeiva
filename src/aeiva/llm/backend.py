from dataclasses import dataclass
from typing import Any, Dict, Optional

from aeiva.llm.api_handlers import ChatAPIHandler, ResponsesAPIHandler, LLMHandler
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.llm.tool_types import ToolCall

MODEL_API_REGISTRY: Dict[str, str] = {
    "codex": "responses",
    "gpt-5-pro": "responses",
    "gpt-5.1-pro": "responses",
    "gpt-5.2-pro": "responses",
    "gpt-5": "chat",
    "gpt-4": "chat",
    "gpt-3.5": "chat",
    "o1-": "chat",
    "o3-": "chat",
}


def _detect_api_type(model_name: str) -> Optional[str]:
    if not model_name:
        return None
    lower = model_name.lower()
    for pattern, api_type in sorted(MODEL_API_REGISTRY.items(), key=lambda x: -len(x[0])):
        if pattern in lower:
            return api_type
    return None


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall]
    response_id: Optional[str]
    usage: Dict[str, Any]
    raw: Any


class LLMBackend:
    def __init__(self, config: LLMGatewayConfig, handler: Optional[LLMHandler] = None):
        self.config = config
        self._handler = handler

    def uses_responses_api(self) -> bool:
        mode = (self.config.llm_api_mode or "auto").lower()
        if mode == "responses":
            return True
        if mode in {"chat", "chat_completion", "completion"}:
            return False

        api_type = _detect_api_type(self.config.llm_model_name or "")
        if api_type:
            return api_type == "responses"

        try:
            from litellm import get_model_info
            return get_model_info((self.config.llm_model_name or "").lower()).get("mode") == "responses"
        except Exception:
            return False

    def _get_handler(self) -> LLMHandler:
        if self._handler is None:
            self._handler = ResponsesAPIHandler(self.config) if self.uses_responses_api() else ChatAPIHandler(self.config)
        return self._handler

    def build_params(self, messages, tools=None, **kwargs):
        return self._get_handler().build_params(messages, tools, **kwargs)

    async def execute(self, params, stream: bool):
        return await self._get_handler().execute(params, stream=stream)

    def execute_sync(self, params):
        return self._get_handler().execute_sync(params)

    def parse_response(self, response) -> LLMResponse:
        _, tool_calls, content = self._get_handler().parse_response(response)
        usage = self._extract_usage(response)
        response_id = self._extract_response_id(response)
        return LLMResponse(
            text=content or "",
            tool_calls=tool_calls or [],
            response_id=response_id,
            usage=usage,
            raw=response,
        )

    def parse_stream_delta(self, chunk, **kwargs):
        return self._get_handler().parse_stream_delta(chunk, **kwargs)

    def _extract_response_id(self, response: Any) -> Optional[str]:
        if isinstance(response, dict):
            return response.get("id")
        return getattr(response, "id", None)

    def _extract_usage(self, response: Any) -> Dict[str, Any]:
        usage = response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
        if not usage:
            return {}
        if isinstance(usage, dict):
            return usage
        return {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0) or 0,
            "completion_tokens": getattr(usage, "completion_tokens", 0) or getattr(usage, "output_tokens", 0) or 0,
            "total_tokens": getattr(usage, "total_tokens", 0) or 0,
        }
