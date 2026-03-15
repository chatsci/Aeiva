from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.llm.tool_types import ToolCallDelta


class LLMProvider(ABC):
    """
    Contract for pluggable LLM providers.

    The ToolLoopEngine only relies on this interface, so provider-specific
    logic stays outside cognition/agent core code.
    """

    provider_name: str = "unknown"
    requires_api_key: bool = True

    def __init__(self, config: LLMGatewayConfig):
        self.config = config

    def validate_config(self) -> None:
        if self.requires_api_key and not self.config.llm_api_key:
            raise ValueError("API key must be provided in the configuration.")

    @abstractmethod
    def uses_responses_api(self) -> bool:
        ...

    @abstractmethod
    def build_params(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def execute(self, params: Dict[str, Any], stream: bool) -> Any:
        ...

    @abstractmethod
    def execute_sync(self, params: Dict[str, Any]) -> Any:
        ...

    @abstractmethod
    def parse_response(self, response: Any) -> Any:
        ...

    @abstractmethod
    def parse_stream_delta(
        self,
        chunk: Any,
        **kwargs,
    ) -> Tuple[Optional[str], Optional[List[ToolCallDelta]]]:
        ...
