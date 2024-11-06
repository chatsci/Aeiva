# lmp.py

import asyncio
from functools import wraps
from typing import Any, Callable, Optional, Dict, List
import os
import sys
from dotenv import load_dotenv

from aeiva.llm.llm_client import LLMClient
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.llm.llm_gateway_exceptions import LLMGatewayError

# Load environment variables from the specified .env file
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key or api_key.startswith("your_ope"):
    print("Error: OPENAI_API_KEY is not set correctly in the .env file.", file=sys.stderr)
    sys.exit(1)

# Initialize LLMGatewayConfig
llm_gateway_config = LLMGatewayConfig(
    llm_model_name="gpt-4",  # Default model
    llm_api_key=api_key,
    llm_base_url="https://api.openai.com/v1",
    llm_timeout=60,
    llm_max_input_tokens=2048,
    llm_max_output_tokens=512,
    llm_temperature=0.7,
    llm_top_p=0.9,
    llm_num_retries=3,
    llm_retry_backoff_factor=2,
    llm_retry_on_status=(429, 500, 502, 503, 504),
    llm_use_async=False,
    llm_stream=False,  # Set to True for streaming responses
    llm_logging_level="INFO",
    llm_additional_params={}
)

# Initialize LLMClient
llm_client = LLMClient(llm_gateway_config)

def simple(model: Optional[str] = None, **llm_params):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract system prompt from docstring
            system_prompt = func.__doc__.strip() if func.__doc__ else ''
            # Generate user prompt
            user_prompt = func(*args, **kwargs)
            # Build messages
            messages = []
            if system_prompt:
                messages.append({'role': 'system', 'content': system_prompt})
            messages.append({'role': 'user', 'content': user_prompt})

            # Update LLM parameters
            params = {}
            if model:
                params['model'] = model
            params.update(llm_params)

            # Check if the LLM is asynchronous
            if llm_gateway_config.llm_use_async:
                # Async version
                async def async_call():
                    try:
                        # Check if streaming is enabled
                        if llm_gateway_config.llm_stream:
                            # Handle streaming response
                            response_stream = llm_client(messages=messages, **params)
                            # Collect the streamed content
                            final_response = ''
                            async for chunk in response_stream:
                                print(chunk, end='', flush=True)
                                final_response += chunk
                            print()  # Newline after streaming completes
                            return final_response
                        else:
                            response = await llm_client.agenerate(messages=messages, **params)
                            return response
                    except LLMGatewayError as e:
                        print(f"An error occurred during LLM generation: {e}", file=sys.stderr)
                        return None
                # Run the async function and return the result
                return asyncio.run(async_call())
            else:
                if llm_gateway_config.llm_stream:
                    raise NotImplementedError("Synchronous streaming is not supported.")
                else:
                    # Synchronous version
                    try:
                        response = llm_client.generate(messages=messages, **params)
                        return response
                    except LLMGatewayError as e:
                        print(f"An error occurred during LLM generation: {e}", file=sys.stderr)
                        return None
        return wrapper
    return decorator

def complex(model: Optional[str] = None, tools: Optional[List[Dict[str, Any]]] = None, **llm_params):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Call the original function to get messages
            result = func(*args, **kwargs)

            # Build messages
            if isinstance(result, str):
                messages = [{'role': 'user', 'content': result}]
            elif isinstance(result, list):
                messages = []
                for item in result:
                    if isinstance(item, dict):
                        messages.append(item)
                    else:
                        raise ValueError("Messages must be dictionaries with 'role' and 'content'")
            else:
                raise ValueError("Function must return a string or a list of messages")

            # Update LLM parameters
            params = {}
            if model:
                params['model'] = model
            params.update(llm_params)

            # Check if the LLM is asynchronous
            if llm_gateway_config.llm_use_async:
                # Async version
                async def async_call():
                    try:
                        # Check if streaming is enabled
                        if llm_gateway_config.llm_stream:
                            # Handle streaming response
                            response_stream = llm_client(messages=messages, tools=tools, **params)
                            # Collect the streamed content
                            final_response = ''
                            async for chunk in response_stream:
                                print(chunk, end='', flush=True)
                                final_response += chunk
                            print()  # Newline after streaming completes
                            return final_response
                        else:
                            response = await llm_client.agenerate(messages=messages, tools=tools, **params)
                            return response
                    except LLMGatewayError as e:
                        print(f"An error occurred during LLM generation: {e}", file=sys.stderr)
                        return None
                # Run the async function and return the result
                return asyncio.run(async_call())
            else:
                if llm_gateway_config.llm_stream:
                    raise NotImplementedError("Synchronous streaming is not supported.")
                else:
                    # Synchronous version
                    try:
                        response = llm_client.generate(messages=messages, tools=tools, **params)
                        return response
                    except LLMGatewayError as e:
                        print(f"An error occurred during LLM generation: {e}", file=sys.stderr)
                        return None
        return wrapper
    return decorator

# Expose llm_client for use in test.py
__all__ = ['simple', 'complex', 'llm_client']