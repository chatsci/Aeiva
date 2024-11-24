import json
import requests
from typing import Dict, Any, AsyncGenerator, List

from litellm import (
    completion as llm_completion,
    acompletion as llm_acompletion,
    supports_function_calling,
)

from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.llm.llm_gateway_exceptions import (
    LLMGatewayError,
    llm_gateway_exception,
)
from aeiva.llm.fault_tolerance import retry_async, retry_sync
from aeiva.logger.logger import get_logger
from aeiva.llm.llm_usage_metrics import LLMUsageMetrics
from aeiva.tool.tool import Tool

# # Enable verbose logging in litellm for debug
# import litellm
# litellm.set_verbose = True

MAX_TOOL_CALL_LOOP = 10 # TODO: This is used in case LLM recursively call tools. Make it a config param. 

class LLMClient:
    """
    Language Model interface that supports synchronous, asynchronous, and streaming modes,
    and optionally, tool usage via function calls.
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
        exceptions=(LLMGatewayError,),  # Catching LLMGatewayError
    )
    def generate(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> str:
        try:
            max_iterations = MAX_TOOL_CALL_LOOP  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Build parameters
                params = self._build_params(messages=messages, tools=tools, **kwargs)
                response = llm_completion(**params)
                self._update_metrics(response)
                response_message = response.choices[0].message

                tool_calls = response_message.tool_calls

                if tool_calls:
                    # Append assistant's tool call message
                    messages.append({"role": "assistant", "tool_calls": tool_calls})

                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        tool_call_id = tool_call.id
                        self.logger.info(f"Tool call id: {tool_call_id}")

                        try:
                            function_response = self.call_tool_sync(
                                api_name=function_name, function_name=function_name, params=function_args
                            )
                        except Exception as e:
                            self.logger.error(f"Error executing tool '{function_name}': {e}")
                            function_response = f"Error executing tool '{function_name}': {e}"

                        # Append the function response to messages
                        messages.append(
                            {
                                "tool_call_id": tool_call_id,
                                "role": "tool",
                                "name": function_name,
                                "content": str(function_response),
                            }
                        )
                    # Continue the loop to handle further function calls
                    continue
                else:
                    # Assistant provided a final response
                    messages.append({"role": "assistant", "content": response_message.content})
                    return response_message.content

            # If loop exceeds max iterations
            raise Exception("Maximum iterations reached without a final response.")

        except Exception as e:
            self.logger.error(f"LLM Gateway Error: {e}")
            raise llm_gateway_exception(e)

    @retry_async(
        max_attempts=lambda self: self.config.llm_num_retries,
        backoff_factor=lambda self: self.config.llm_retry_backoff_factor,
        exceptions=(LLMGatewayError,),  # Catching LLMGatewayError
    )
    async def agenerate(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> str:
        try:
            max_iterations = MAX_TOOL_CALL_LOOP  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Build parameters
                params = self._build_params(messages=messages, tools=tools, **kwargs)
                response = await llm_acompletion(**params)
                self._update_metrics(response)
                response_message = response.choices[0].message

                tool_calls = response_message.tool_calls

                if tool_calls:
                    # Append assistant's tool call message
                    messages.append({"role": "assistant", "tool_calls": tool_calls})

                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        tool_call_id = tool_call.id

                        try:
                            function_response = await self.call_tool(
                                api_name=function_name, function_name=function_name, params=function_args
                            )
                        except Exception as e:
                            self.logger.error(f"Error executing tool '{function_name}': {e}")
                            function_response = f"Error executing tool '{function_name}': {e}"

                        # Append the function response to messages
                        messages.append(
                            {
                                "tool_call_id": tool_call_id,
                                "role": "tool",
                                "name": function_name,
                                "content": str(function_response),
                            }
                        )
                    # Continue the loop to handle further function calls
                    continue
                else:
                    # Assistant provided a final response
                    messages.append({"role": "assistant", "content": response_message.content})
                    return response_message.content

            # If loop exceeds max iterations
            raise Exception("Maximum iterations reached without a final response.")

        except Exception as e:
            self.logger.error(f"LLM Asynchronous Generation Error: {e}")
            raise llm_gateway_exception(e)

    async def stream_generate(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> AsyncGenerator[str, None]:
        try:
            max_iterations = MAX_TOOL_CALL_LOOP  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Build parameters
                params = self._build_params(messages=messages, tools=tools, **kwargs)
                response_stream = await llm_acompletion(**params)

                # Prepare to collect the assistant's reply
                tool_calls = []  # Accumulator for tool calls
                full_delta_content = ''  # Accumulator for assistant's content

                # Collect streamed responses
                async for response in response_stream:
                    delta = response.choices[0].delta

                    # Collect assistant's content and yield it
                    if getattr(delta, 'content', None):
                        full_delta_content += delta.content
                        yield delta.content

                    # Check for tool calls in the delta
                    if getattr(delta, 'tool_calls', None):
                        tc_chunk_list = delta.tool_calls
                        for tc_chunk in tc_chunk_list:
                            index = tc_chunk.index
                            # Ensure tool_calls list is large enough
                            while len(tool_calls) <= index:
                                tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                            tc = tool_calls[index]

                            if getattr(tc_chunk, 'id', None):
                                tc["id"] += tc_chunk.id
                            if getattr(tc_chunk.function, 'name', None):
                                tc["function"]["name"] += tc_chunk.function.name
                            if getattr(tc_chunk.function, 'arguments', None):
                                tc["function"]["arguments"] += tc_chunk.function.arguments

                # After initial streaming, check if there are tool calls
                if tool_calls:
                    # Append the assistant's tool_call message to messages
                    messages.append({"role": "assistant", "tool_calls": tool_calls})

                    # Process each tool_call
                    available_functions = [tool["function"]["name"] for tool in tools]
                    for tool_call in tool_calls:
                        function_name = tool_call["function"]["name"]
                        if function_name not in available_functions:
                            # Handle error if function not found
                            yield f"Function {function_name} does not exist."
                            return
                        # Call the function with arguments
                        try:
                            function_args = json.loads(tool_call["function"]["arguments"])
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Error decoding function arguments: {e}")
                            function_args = {}

                        try:
                            function_response = await self.call_tool(
                                api_name=function_name, function_name=function_name, params=function_args
                            )
                        except Exception as e:
                            self.logger.error(f"Error executing tool '{function_name}': {e}")
                            function_response = f"Error executing tool '{function_name}': {e}"

                        # Append the function's response to messages
                        messages.append(
                            {
                                "tool_call_id": tool_call['id'],
                                "role": "tool",
                                "name": function_name,
                                "content": str(function_response),
                            }
                        )
                    # Continue the loop to handle further function calls
                    continue
                else:
                    # No tool calls, streaming is complete
                    messages.append({"role": "assistant", "content": full_delta_content})
                    return  # Exit the loop

            # If loop exceeds max iterations
            yield "Maximum iterations reached without a final response."

        except Exception as e:
            self.logger.error(f"Streaming LLM Gateway Error: {e}")
            yield "An error occurred during streaming."

    def call_tool_via_server(self, api_name: str, function_name: str, params: Dict[str, Any]) -> Any: # TODO: may need revise
        """Calls the API via FastAPI server."""
        url = f"http://localhost:8000/api/{api_name}/{function_name}"
        self.logger.info(f"Calling {api_name} with params: {params}")
        response = requests.get(url, params=params)
        if response.status_code == 200:
            json_response = response.json()
            if "result" in json_response:
                return str(json_response["result"])
            else:
                return f"Error from API: {json_response.get('error', 'Unknown error')}"
        else:
            return f"HTTP Error {response.status_code}: {response.text}"

    async def call_tool(self, api_name: str, function_name: str, params: Dict[str, Any]) -> Any: # TODO: may need revise
        """Calls the API via action module."""
        tool = Tool(api_name)
        return await tool.aexecute(params)
    
    def call_tool_sync(self, api_name: str, function_name: str, params: Dict[str, Any]) -> Any: # TODO: may need revise
        """Calls the API via action module."""
        tool = Tool(api_name)
        return tool.execute(params)

    def _build_params(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        params = {
            "model": self.config.llm_model_name,
            "messages": messages,
            "api_key": self.config.llm_api_key,
            "temperature": self.config.llm_temperature,
            "top_p": self.config.llm_top_p,
            "max_tokens": self.config.llm_max_output_tokens,
            "timeout": self.config.llm_timeout,
        }
        params.update(self.config.llm_additional_params)
        params.update(kwargs)

        # Check if the model supports function calling
        if tools and supports_function_calling(self.config.llm_model_name):
            params["tools"] = tools
            params["tool_choice"] = "auto"

        return params

    def _update_metrics(self, response: Any, log: bool = False):  # Note: log is False by default. Adjust according to the need.
        usage = getattr(response, "usage", {})
        self.metrics.add_tokens(
            prompt_tokens=getattr(usage, "prompt_tokens", 0),
            completion_tokens=getattr(usage, "completion_tokens", 0),
        )
        self.metrics.add_cost(getattr(usage, "cost", 0.0))
        if log:
            self.logger.info(
                f"Tokens used: {self.metrics.total_tokens}, Cost: ${self.metrics.total_cost:.4f}"
            )

    def __call__(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> Any:
        if self.config.llm_use_async:
            if self.config.llm_stream:
                return self.stream_generate(messages, tools=tools, **kwargs)
            else:
                return self.agenerate(messages, tools=tools, **kwargs)
        else:
            if self.config.llm_stream:
                # OpenAI's API does not support synchronous streaming; streaming must be async
                raise NotImplementedError("Synchronous streaming is not supported.")
            else:
                return self.generate(messages, tools=tools, **kwargs)