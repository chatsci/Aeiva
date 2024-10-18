# src/aeiva/llm/test.py

import os
import sys
import asyncio
from dotenv import load_dotenv

from aeiva.cognition.brain.llm.llm_client_old import LLMClient
from aeiva.cognition.brain.llm.llm_gateway_config import LLMGatewayConfig  # Import LLMConfig
from aeiva.cognition.brain.llm.llm_gateway_exceptions import LLMGatewayError


def initialize_llm_client(llm_use_async: bool, llm_stream: bool) -> LLMClient:
    # Load environment variables from the specified .env file
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key or api_key.startswith("your_ope"):
        print("Error: OPENAI_API_KEY is not set correctly in the .env file.", file=sys.stderr)
        sys.exit(1)
    
    llm_gateway_config = LLMGatewayConfig(
        llm_model_name="gpt-4",  # Specify your desired model
        llm_api_key=api_key,  # Use the loaded API key
        llm_base_url="https://api.openai.com/v1",
        llm_api_version="v1",
        llm_embedding_model="text-embedding-ada-002",
        llm_timeout=60,
        llm_max_input_tokens=2048,
        llm_max_output_tokens=512,
        llm_temperature=0.7,
        llm_top_p=0.9,
        llm_num_retries=3,
        llm_retry_backoff_factor=2,
        llm_retry_on_status=(429, 500, 502, 503, 504),
        llm_use_async=llm_use_async,
        llm_stream=llm_stream,
        llm_logging_level="INFO",
        llm_additional_params={}
    )
    
    llm = LLMClient(llm_gateway_config)
    return llm

def test_sync_non_streaming(llm: LLMClient, prompt: str):
    try:
        response = llm(prompt)
        print("\n=== Synchronous Non-Streaming Response ===")
        print(response)
    except LLMGatewayError as e:
        print(f"An error occurred during synchronous non-streaming LLM generation: {e}", file=sys.stderr)

async def test_async_non_streaming(llm: LLMClient, prompt: str):
    try:
        response = await llm(prompt)
        print("\n=== Asynchronous Non-Streaming Response ===")
        print(response)
    except LLMGatewayError as e:
        print(f"An error occurred during asynchronous non-streaming LLM generation: {e}", file=sys.stderr)

async def test_async_streaming(llm: LLMClient, prompt: str):
    try:
        print("\n=== Asynchronous Streaming Response ===")
        async for token in llm.stream_generate(prompt):
            print(token, end='', flush=True)
        print()  # For newline after streaming
    except LLMGatewayError as e:
        print(f"An error occurred during asynchronous streaming LLM generation: {e}", file=sys.stderr)

def main():
    prompt = "Tell me a story about a brave knight."
    
    # Test 1: Synchronous Non-Streaming
    print("Initializing LLM for Synchronous Non-Streaming Mode...")
    llm_sync = initialize_llm_client(llm_use_async=False, llm_stream=False)
    test_sync_non_streaming(llm_sync, prompt)
    
    # Test 2: Asynchronous Non-Streaming
    print("\nInitializing LLM for Asynchronous Non-Streaming Mode...")
    llm_async = initialize_llm_client(llm_use_async=True, llm_stream=False)
    
    # Test 3: Asynchronous Streaming
    print("\nInitializing LLM for Asynchronous Streaming Mode...")
    llm_async_stream = initialize_llm_client(llm_use_async=True, llm_stream=True)
    
    # Run async tests
    asyncio.run(async_tests(llm_async, llm_async_stream, prompt))

async def async_tests(llm_async: LLMClient, llm_async_stream: LLMClient, prompt: str):
    await test_async_non_streaming(llm_async, prompt)
    await test_async_streaming(llm_async_stream, prompt)

if __name__ == "__main__":
    main()