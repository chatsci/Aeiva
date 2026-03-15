from __future__ import annotations

from typing import Any, Dict, List, Optional

from aeiva.llm.backend import LLMBackend
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.llm.providers.base import LLMProvider


class LiteLLMProvider(LLMProvider):
    """
    Default provider backed by AEIVA's existing LiteLLM gateway backend.
    """

    provider_name = "litellm"
    requires_api_key = True

    def __init__(self, config: LLMGatewayConfig):
        super().__init__(config)
        self._backend = LLMBackend(config)

    @property
    def backend(self) -> LLMBackend:
        return self._backend

    def uses_responses_api(self) -> bool:
        return self._backend.uses_responses_api()

    def build_params(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        return self._backend.build_params(messages, tools=tools, **kwargs)

    async def execute(self, params: Dict[str, Any], stream: bool) -> Any:
        return await self._backend.execute(params, stream=stream)

    def execute_sync(self, params: Dict[str, Any]) -> Any:
        return self._backend.execute_sync(params)

    def parse_response(self, response: Any) -> Any:
        return self._backend.parse_response(response)

    def parse_stream_delta(self, chunk: Any, **kwargs):
        return self._backend.parse_stream_delta(chunk, **kwargs)
