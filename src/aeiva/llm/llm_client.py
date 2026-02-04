"""
LLM Client - Unified interface for language model interactions.

Thin facade over the ToolLoopEngine and LiteLLM adapter.
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import litellm

from aeiva.llm.adapters.litellm_adapter import LiteLLMAdapter
from aeiva.llm.fault_tolerance import retry_async, retry_sync
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.llm.llm_gateway_exceptions import LLMGatewayError, llm_gateway_exception
from aeiva.llm.llm_usage_metrics import LLMUsageMetrics
from aeiva.llm.patches import apply_all_patches
from aeiva.llm.tool_loop import ToolLoopEngine, ToolLoopResult


class LLMClient:
    """
    Unified LLM interface supporting sync, async, and streaming modes.

    Delegates tool calling and iteration logic to ToolLoopEngine.
    """

    DEFAULT_MAX_TOOL_LOOPS = 10

    def __init__(self, config: LLMGatewayConfig):
        self.config = config
        self.metrics = LLMUsageMetrics()
        self.logger = logging.getLogger(__name__)

        if not self.config.llm_api_key:
            raise ValueError("API key must be provided in the configuration.")

        apply_all_patches()
        litellm.drop_params = True
        self._configure_litellm()

        self.adapter = LiteLLMAdapter(self.config)
        self.engine = ToolLoopEngine(
            adapter=self.adapter,
            metrics=self.metrics,
            max_tool_loops=self.max_tool_loops,
        )

    @property
    def max_tool_loops(self) -> int:
        return getattr(self.config, "llm_max_tool_loops", self.DEFAULT_MAX_TOOL_LOOPS)

    @property
    def last_response_id(self) -> Optional[str]:
        return self.engine.last_response_id

    def _configure_litellm(self) -> None:
        if hasattr(litellm, "suppress_debug_info"):
            litellm.suppress_debug_info = True
        if self.config.llm_api_key:
            litellm.api_key = self.config.llm_api_key
            litellm.openai_key = self.config.llm_api_key

    # ---------------------------------------------------------------------
    # Public API (preferred)
    # ---------------------------------------------------------------------

    @retry_sync(
        max_attempts=lambda self: self.config.llm_num_retries,
        backoff_factor=lambda self: self.config.llm_retry_backoff_factor,
        exceptions=(LLMGatewayError,),
    )
    def run(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> ToolLoopResult:
        try:
            return self.engine.run(messages, tools=tools, **kwargs)
        except Exception as e:
            self.logger.error(f"Generation error: {e}")
            raise llm_gateway_exception(e)

    @retry_async(
        max_attempts=lambda self: self.config.llm_num_retries,
        backoff_factor=lambda self: self.config.llm_retry_backoff_factor,
        exceptions=(LLMGatewayError,),
    )
    async def arun(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> ToolLoopResult:
        try:
            return await self.engine.arun(messages, tools=tools, **kwargs)
        except Exception as e:
            self.logger.error(f"Async generation error: {e}")
            raise llm_gateway_exception(e)

    async def astream(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> AsyncGenerator[str, None]:
        try:
            async for delta in self.engine.astream(messages, tools=tools, **kwargs):
                yield delta
        except Exception as e:
            self.logger.error(f"Streaming error: {e}")
            try:
                result = await self.arun(messages, tools=tools, stream=False, **kwargs)
                if result.text:
                    yield result.text
                    return
            except Exception:
                pass
            yield f"Streaming error: {e}"

    # ---------------------------------------------------------------------
    # Backward-compatible wrappers
    # ---------------------------------------------------------------------

    def generate(self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs) -> str:
        return self.run(messages, tools=tools, **kwargs).text

    async def agenerate(self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs) -> str:
        return (await self.arun(messages, tools=tools, **kwargs)).text

    async def stream_generate(self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs) -> AsyncGenerator[str, None]:
        async for delta in self.astream(messages, tools=tools, **kwargs):
            yield delta

    def __call__(self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs) -> Any:
        use_async = kwargs.pop("use_async", self.config.llm_use_async)
        stream = kwargs.setdefault("stream", self.config.llm_stream)

        if use_async:
            return self.astream(messages, tools=tools, **kwargs) if stream else self.arun(messages, tools=tools, **kwargs)

        if stream:
            raise NotImplementedError("Synchronous streaming is not supported.")
        return self.run(messages, tools=tools, **kwargs).text
