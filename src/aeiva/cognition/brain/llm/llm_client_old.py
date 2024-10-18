from typing import Dict, Any, AsyncGenerator

from litellm import completion as llm_completion
from litellm import acompletion as llm_acompletion

from aeiva.cognition.brain.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.cognition.brain.llm.llm_gateway_exceptions import LLMGatewayError, llm_gateway_exception
from aeiva.cognition.brain.llm.fault_tolerance import retry_async, retry_sync
from aeiva.logger.logger import get_logger
from aeiva.cognition.brain.llm.llm_usage_metrics import LLMUsageMetrics


class LLMClient:
    """
    Language Model interface that supports synchronous, asynchronous, and streaming modes.
    """

    def __init__(self, config: LLMGatewayConfig):
        self.config = config
        self.metrics = LLMUsageMetrics()
        self.logger = get_logger(__name__, level=config.llm_logging_level.upper())
        self._validate_config()

    def _validate_config(self):
        if not self.config.llm_api_key:
            raise ValueError("API key must be provided in the configuration.")

    @retry_sync(
        max_attempts=lambda self: self.config.llm_num_retries,
        backoff_factor=lambda self: self.config.llm_retry_backoff_factor,
        exceptions=(LLMGatewayError,),  # Now only catching LLMGatewayError
    )
    def generate(self, prompt: str, **kwargs) -> str:
        try:
            params = self._build_params(prompt, **kwargs)
            response = llm_completion(**params)
            self._update_metrics(response)
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"LLM Gateway Error: {e}")
            raise llm_gateway_exception(e)

    @retry_async(
        max_attempts=lambda self: self.config.llm_num_retries,
        backoff_factor=lambda self: self.config.llm_retry_backoff_factor,
        exceptions=(LLMGatewayError,),  # Now only catching LLMGatewayError
    )
    async def agenerate(self, prompt: str, **kwargs) -> str:
        try:
            params = self._build_params(prompt, **kwargs)
            response = await llm_acompletion(**params)
            self._update_metrics(response)
            # Correctly access the message content
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"LLM Asynchronous Generation Error: {e}")
            raise llm_gateway_exception(e)

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        try:
            params = self._build_params(prompt, stream=True, **kwargs)
            resp = await llm_acompletion(**params)
            async for response in resp:
                self._update_metrics(response, log=False)  # Suppress logging
                if response.choices and response.choices[0].delta and 'content' in response.choices[0].delta:
                    yield response.choices[0].delta.content
                else:
                    yield ""
        except Exception as e:
            self.logger.error(f"LLM Streaming Generation Error: {e}")
            raise llm_gateway_exception(e)

    def _build_params(self, prompt: str, **kwargs) -> Dict[str, Any]:
        params = {
            'model': self.config.llm_model_name,
            'messages': [{'role': 'user', 'content': prompt}],  # Correctly set 'messages'
            'api_key': self.config.llm_api_key,
            'temperature': self.config.llm_temperature,
            'top_p': self.config.llm_top_p,
            'max_tokens': self.config.llm_max_output_tokens,
            'timeout': self.config.llm_timeout,
        }
        params.update(self.config.llm_additional_params)
        params.update(kwargs)
        return params

    def _update_metrics(self, response: Any, log: bool = True):
        usage = getattr(response, 'usage', {})
        self.metrics.add_tokens(
            prompt_tokens=getattr(usage, 'prompt_tokens', 0),
            completion_tokens=getattr(usage, 'completion_tokens', 0),
        )
        self.metrics.add_cost(getattr(usage, 'cost', 0.0))
        if log:
            self.logger.info(f"Tokens used: {self.metrics.total_tokens}, Cost: ${self.metrics.total_cost:.4f}")

    def __call__(self, prompt: str, **kwargs) -> Any:
        if self.config.llm_use_async:
            if self.config.llm_stream:
                raise LLMGatewayError("Streaming is only supported via the 'stream_generate' method.")
            else:
                return self.agenerate(prompt, **kwargs)
        else:
            if self.config.llm_stream:
                raise LLMGatewayError("Streaming is only supported in asynchronous mode.")
            else:
                return self.generate(prompt, **kwargs)