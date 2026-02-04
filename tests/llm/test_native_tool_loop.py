import json
import pytest

from aeiva.llm.llm_client import LLMClient
from aeiva.llm.llm_gateway_config import LLMGatewayConfig


class FakeHandler:
    def __init__(self):
        self.calls = 0

    def build_params(self, messages, tools, **kwargs):
        return {"messages": messages, "tools": tools}

    async def execute(self, params, stream=False):
        return {"ok": True}

    def execute_sync(self, params):
        return {"ok": True}

    def parse_response(self, response):
        # First call: request tool
        if self.calls == 0:
            self.calls += 1
            return None, [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "filesystem",
                        "arguments": json.dumps({"operation": "list", "path": "/tmp"}),
                    },
                }
            ], ""
        # Second call: final content
        return None, [], "Final answer"


@pytest.mark.asyncio
async def test_native_tool_loop_chat(monkeypatch):
    cfg = LLMGatewayConfig(llm_model_name="gpt-4o", llm_api_key="test")
    client = LLMClient(cfg)

    handler = FakeHandler()
    monkeypatch.setattr(client, "_get_handler", lambda: handler)

    calls = []

    async def fake_call_tool(name, params):
        calls.append((name, params))
        return {"ok": True}

    monkeypatch.setattr(client, "call_tool", fake_call_tool)

    messages = [{"role": "user", "content": "hi"}]
    result = await client.agenerate(messages, tools=[{"type": "function", "function": {"name": "filesystem"}}])

    assert result == "Final answer"
    assert calls == [("filesystem", {"operation": "list", "path": "/tmp"})]
    # Ensure tool result appended to messages
    assert any(m.get("role") == "tool" for m in messages)


@pytest.mark.asyncio
async def test_native_tool_loop_responses(monkeypatch):
    cfg = LLMGatewayConfig(
        llm_model_name="gpt-5.2",
        llm_api_key="test",
        llm_api_mode="responses",
    )
    client = LLMClient(cfg)

    handler = FakeHandler()
    monkeypatch.setattr(client, "_get_handler", lambda: handler)

    calls = []

    async def fake_call_tool(name, params):
        calls.append((name, params))
        return {"ok": True}

    monkeypatch.setattr(client, "call_tool", fake_call_tool)

    messages = [{"role": "user", "content": "hi"}]
    result = await client.agenerate(messages, tools=[{"type": "function", "function": {"name": "filesystem"}}])

    assert result == "Final answer"
    assert calls == [("filesystem", {"operation": "list", "path": "/tmp"})]
    assert any(m.get("role") == "tool" for m in messages)


@pytest.mark.asyncio
async def test_tool_calls_route_through_registry(monkeypatch):
    cfg = LLMGatewayConfig(llm_model_name="gpt-4o", llm_api_key="test")
    client = LLMClient(cfg)

    handler = FakeHandler()
    monkeypatch.setattr(client, "_get_handler", lambda: handler)

    class DummyRegistry:
        def __init__(self):
            self.called = []

        async def execute(self, name, **kwargs):
            self.called.append((name, kwargs))
            return {"ok": True}

    registry = DummyRegistry()
    monkeypatch.setattr("aeiva.llm.llm_client.get_registry", lambda: registry)

    messages = [{"role": "user", "content": "hi"}]
    result = await client.agenerate(messages, tools=[{"type": "function", "function": {"name": "filesystem"}}])

    assert result == "Final answer"
    assert registry.called == [("filesystem", {"operation": "list", "path": "/tmp"})]
