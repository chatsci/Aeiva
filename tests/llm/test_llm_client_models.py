"""
Tests for LLMClient with various GPT models.

Tests cover:
- API detection (chat/completions vs responses API)
- Strategy parameter building and response parsing
- Streaming and non-streaming modes
- Action/tool-requiring prompts
"""

import asyncio
import os
import pytest
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock, AsyncMock

from aeiva.llm.llm_client import LLMClient
from aeiva.llm.backend import MODEL_API_REGISTRY, _detect_api_type
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.llm.api_handlers import ChatAPIHandler, ResponsesAPIHandler


# ============================================================
# Test Data
# ============================================================

MODELS_CHAT_API = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-5",
    "gpt-5-mini",
    "o1-preview",
    "o1-mini",
    "o3-mini",
]

MODELS_RESPONSES_API = [
    "gpt-5-codex",
    "gpt-5.1-codex",
    "gpt-5.1-codex-mini",
]

ALL_MODELS = MODELS_CHAT_API + MODELS_RESPONSES_API


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_api_key():
    return "test-api-key-12345"


@pytest.fixture
def make_config(mock_api_key):
    """Factory to create LLMGatewayConfig with given model."""
    def _make(model_name: str, **kwargs) -> LLMGatewayConfig:
        return LLMGatewayConfig(
            llm_api_key=mock_api_key,
            llm_model_name=model_name,
            **kwargs
        )
    return _make


@pytest.fixture
def make_client(make_config):
    """Factory to create LLMClient with given model."""
    def _make(model_name: str, **kwargs) -> LLMClient:
        config = make_config(model_name, **kwargs)
        return LLMClient(config)
    return _make


# ============================================================
# API Detection Tests
# ============================================================

class TestAPIDetection:
    """Test that correct API is detected for each model."""

    @pytest.mark.parametrize("model", MODELS_CHAT_API)
    def test_chat_api_models(self, make_client, model):
        """Models that should use chat/completions API."""
        client = make_client(model)
        assert client.uses_responses_api() is False, f"{model} should use chat API"

    @pytest.mark.parametrize("model", MODELS_RESPONSES_API)
    def test_responses_api_models(self, make_client, model):
        """Models that should use responses API."""
        client = make_client(model)
        assert client.uses_responses_api() is True, f"{model} should use responses API"

    def test_explicit_mode_responses(self, make_client):
        """Explicit 'responses' mode overrides auto-detection."""
        client = make_client("gpt-4o", llm_api_mode="responses")
        assert client.uses_responses_api() is True

    def test_explicit_mode_chat(self, make_client):
        """Explicit 'chat' mode overrides auto-detection."""
        client = make_client("gpt-5-codex", llm_api_mode="chat")
        assert client.uses_responses_api() is False

    def test_auto_mode_default(self, make_client):
        """Auto mode uses model info for detection."""
        client = make_client("gpt-4o", llm_api_mode="auto")
        assert client.uses_responses_api() is False

    def test_registry_detection(self):
        """Test _detect_api_type function directly."""
        assert _detect_api_type("gpt-4o") == "chat"
        assert _detect_api_type("gpt-5-codex") == "responses"
        assert _detect_api_type("gpt-5-pro") == "responses"
        assert _detect_api_type("unknown-model") is None


# ============================================================
# Strategy Parameter Building Tests
# ============================================================

class TestChatAPIHandler:
    """Test ChatAPIHandler parameter building and parsing."""

    def test_build_params_basic(self, make_config):
        """Basic params are built correctly."""
        config = make_config("gpt-4o")
        strategy = ChatAPIHandler(config)
        messages = [{"role": "user", "content": "Hello"}]

        params = strategy.build_params(messages)

        assert params["model"] == "gpt-4o"
        assert params["messages"] == messages
        assert "api_key" in params

    def test_build_params_with_tools(self, make_config):
        """Tools are added when model supports function calling."""
        config = make_config("gpt-4o")
        config.llm_tool_choice = "auto"
        strategy = ChatAPIHandler(config)
        messages = [{"role": "user", "content": "Hello"}]
        tools = [{"type": "function", "function": {"name": "test", "parameters": {}}}]

        params = strategy.build_params(messages, tools=tools)

        assert "tools" in params
        assert params["tool_choice"] == "auto"

    def test_parse_response_choices(self):
        """Parse response from standard choices format."""
        config = LLMGatewayConfig(llm_api_key="test", llm_model_name="gpt-4o")
        strategy = ChatAPIHandler(config)

        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Hello, world!"
        mock_message.tool_calls = None
        mock_response.choices = [MagicMock(message=mock_message)]

        message, tool_calls, content = strategy.parse_response(mock_response)

        assert content == "Hello, world!"
        assert tool_calls == []

    def test_parse_response_dict(self):
        """Parse response from dict format."""
        config = LLMGatewayConfig(llm_api_key="test", llm_model_name="gpt-4o")
        strategy = ChatAPIHandler(config)

        response = {
            "choices": [{
                "message": {
                    "content": "Test response",
                    "tool_calls": None
                }
            }]
        }

        message, tool_calls, content = strategy.parse_response(response)
        assert content == "Test response"

    def test_parse_stream_delta_choices(self):
        """Parse streaming delta from choices format."""
        config = LLMGatewayConfig(llm_api_key="test", llm_model_name="gpt-4o")
        strategy = ChatAPIHandler(config)

        mock_chunk = MagicMock()
        mock_delta = MagicMock()
        mock_delta.content = "chunk"
        mock_delta.tool_calls = None
        mock_chunk.choices = [MagicMock(delta=mock_delta)]

        content, tool_calls = strategy.parse_stream_delta(mock_chunk)

        assert content == "chunk"

    def test_parse_stream_delta_dict(self):
        """Parse streaming delta from dict format."""
        config = LLMGatewayConfig(llm_api_key="test", llm_model_name="gpt-4o")
        strategy = ChatAPIHandler(config)

        chunk = {
            "choices": [{
                "delta": {"content": "streamed"}
            }]
        }

        content, tool_calls = strategy.parse_stream_delta(chunk)
        assert content == "streamed"

    def test_filter_supported_params(self, make_config):
        """Required params should not be filtered."""
        config = make_config("gpt-4o")
        strategy = ChatAPIHandler(config)
        params = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "test"}],
            "api_key": "test-key",
            "temperature": 0.7,
        }

        filtered = strategy._filter_supported_params(params.copy())

        assert "model" in filtered
        assert "messages" in filtered
        assert "api_key" in filtered


class TestResponsesAPIHandler:
    """Test ResponsesAPIHandler parameter building and parsing."""

    def test_build_params_basic(self, make_config):
        """Responses API params are built correctly."""
        config = make_config("gpt-5-codex")
        strategy = ResponsesAPIHandler(config)
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"}
        ]

        params = strategy.build_params(messages)

        assert "input" in params
        assert "instructions" in params

    def test_build_params_with_tools_normalizes(self, make_config):
        config = make_config("gpt-5-codex")
        strategy = ResponsesAPIHandler(config)
        messages = [{"role": "user", "content": "Hello"}]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "filesystem",
                    "description": "List files",
                    "parameters": {"type": "object", "properties": {"path": {"type": "string"}}},
                },
            }
        ]

        params = strategy.build_params(messages, tools=tools)

        assert "tools" in params
        assert params["tools"][0]["name"] == "filesystem"
        assert "function" not in params["tools"][0]

    def test_parse_stream_delta_function_call_item(self, make_config):
        config = make_config("gpt-5-codex")
        strategy = ResponsesAPIHandler(config)

        chunk = {
            "type": "response.output_item.added",
            "item": {
                "type": "function_call",
                "call_id": "call_1",
                "name": "filesystem",
                "arguments": "{\"operation\":\"list\",\"path\":\"/tmp\"}",
            },
        }

        content, deltas = strategy.parse_stream_delta(chunk)
        assert content is None
        assert deltas
        assert deltas[0].name == "filesystem"

    def test_parse_stream_delta_ignores_function_call_arguments_delta(self, make_config):
        config = make_config("gpt-5-codex")
        strategy = ResponsesAPIHandler(config)

        chunk = {
            "type": "response.function_call_arguments.delta",
            "delta": "{\"operation\":\"list\"}",
        }

        content, deltas = strategy.parse_stream_delta(chunk)
        assert content is None
        assert deltas is None

    def test_parse_stream_delta_function_call_arguments_done(self, make_config):
        config = make_config("gpt-5-codex")
        strategy = ResponsesAPIHandler(config)

        chunk = {
            "type": "response.function_call_arguments.done",
            "call_id": "call_2",
            "name": "filesystem",
            "arguments": "{\"operation\":\"list\",\"path\":\"/tmp\"}",
        }

        content, deltas = strategy.parse_stream_delta(chunk)
        assert content is None
        assert deltas
        assert deltas[0].name == "filesystem"

    def test_normalize_string_input(self, make_config):
        """String input passes through."""
        config = make_config("gpt-5-codex")
        strategy = ResponsesAPIHandler(config)

        input_items, instructions = strategy._normalize_input("Hello")

        assert input_items == "Hello"
        assert instructions is None

    def test_normalize_messages_with_system(self, make_config):
        """System messages become instructions."""
        config = make_config("gpt-5-codex")
        strategy = ResponsesAPIHandler(config)
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"}
        ]

        input_items, instructions = strategy._normalize_input(messages)

        assert instructions == "You are helpful"
        assert len(input_items) == 1
        assert input_items[0]["role"] == "user"

    def test_normalize_multimodal_content(self, make_config):
        """Multimodal content is converted correctly."""
        config = make_config("gpt-5-codex")
        strategy = ResponsesAPIHandler(config)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is this?"},
                    {"type": "image_url", "image_url": {"url": "http://example.com/img.png"}}
                ]
            }
        ]

        input_items, instructions = strategy._normalize_input(messages)

        assert len(input_items) == 1
        assert len(input_items[0]["content"]) == 2

    def test_parse_response_output_text(self):
        """Parse response with output_text."""
        config = LLMGatewayConfig(llm_api_key="test", llm_model_name="gpt-5-codex")
        strategy = ResponsesAPIHandler(config)

        response = {"output_text": "Responses API output"}
        message, tool_calls, content = strategy.parse_response(response)

        assert content == "Responses API output"


# ============================================================
# Parameter Filtering Tests
# ============================================================

class TestParameterFiltering:
    """Test that unsupported parameters are handled correctly."""

    def test_drop_params_enabled(self):
        """Verify litellm.drop_params is enabled."""
        import litellm
        assert litellm.drop_params is True, "drop_params should be enabled for model compatibility"


# ============================================================
# Integration Tests (require API key)
# ============================================================

@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)
class TestIntegration:
    """Integration tests with real API calls."""

    @pytest.fixture
    def real_client(self):
        """Create client with real API key."""
        def _make(model: str) -> LLMClient:
            config = LLMGatewayConfig(
                llm_api_key=os.getenv("OPENAI_API_KEY"),
                llm_model_name=model,
                llm_timeout=120,
                llm_temperature=0.7,
                llm_max_output_tokens=100,
            )
            return LLMClient(config)
        return _make

    @pytest.mark.asyncio
    @pytest.mark.parametrize("model", ["gpt-4o-mini"])
    async def test_simple_chat(self, real_client, model):
        """Simple chat works with real API."""
        client = real_client(model)
        messages = [{"role": "user", "content": "Say 'test' and nothing else"}]

        response = await client.agenerate(messages)

        assert response is not None
        assert len(response) > 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("model", ["gpt-4o-mini"])
    async def test_streaming(self, real_client, model):
        """Streaming works with real API."""
        client = real_client(model)
        messages = [{"role": "user", "content": "Say 'hello' and nothing else"}]

        chunks = []
        async for chunk in client.stream_generate(messages, stream=True):
            chunks.append(chunk)

        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert len(full_response) > 0


# ============================================================
# Tool Registry Integration Tests
# ============================================================

class TestToolRegistryIntegration:
    """Test LLMClient integration with tool registry."""

    @pytest.mark.asyncio
    async def test_call_tool(self, make_client):
        """call_tool executes via registry."""
        from aeiva.tool.registry import get_registry

        client = make_client("gpt-4o")
        registry = get_registry()

        if "calculator" in registry:
            result = await client.call_tool("calculator", {"expression": "2+2"})
            assert result.get("result") == 4

    def test_call_tool_sync(self, make_client):
        """call_tool_sync executes synchronously."""
        from aeiva.tool.registry import get_registry

        client = make_client("gpt-4o")
        registry = get_registry()

        if "calculator" in registry:
            result = client.call_tool_sync("calculator", {"expression": "3*3"})
            assert result.get("result") == 9


# ============================================================
# Error Handling Tests
# ============================================================

class TestErrorHandling:
    """Test error handling in LLMClient."""

    def test_missing_api_key(self):
        """Missing API key raises ValueError."""
        config = LLMGatewayConfig(llm_api_key=None)

        with pytest.raises(ValueError, match="API key"):
            LLMClient(config)

    @pytest.mark.asyncio
    async def test_timeout_handling(self, make_client):
        """Timeout is handled gracefully."""
        client = make_client("gpt-4o", llm_timeout=1)  # 1 second timeout

        # This should either succeed quickly or timeout gracefully
        # We can't easily test actual timeout without mocking
        assert client.config.llm_timeout == 1
