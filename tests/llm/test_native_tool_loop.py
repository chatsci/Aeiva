import json
import pytest

from aeiva.llm.adapters.base import AdapterResponse
from aeiva.llm.llm_client import LLMClient
from aeiva.llm.tool_loop import ToolLoopEngine
from aeiva.llm.llm_gateway_config import LLMGatewayConfig


class FakeAdapter:
    def __init__(self):
        self.calls = 0

    def build_params(self, messages, tools=None, **kwargs):
        return {"messages": messages, "tools": tools}

    async def execute(self, params, stream: bool = False):
        return {"ok": True}

    def execute_sync(self, params):
        return {"ok": True}

    def parse_response(self, response):
        if self.calls == 0:
            self.calls += 1
            tool_calls = [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "filesystem",
                        "arguments": json.dumps({"operation": "list", "path": "/tmp"}),
                    },
                }
            ]
            return AdapterResponse("", tool_calls, "resp_1", {}, response)

        return AdapterResponse("Final answer", [], "resp_2", {}, response)

    def parse_stream_delta(self, chunk, **kwargs):
        return None, None


@pytest.mark.asyncio
async def test_tool_loop_engine_executes_tools():
    adapter = FakeAdapter()

    class DummyRegistry:
        def __init__(self):
            self.called = []

        async def execute(self, name, **kwargs):
            self.called.append((name, kwargs))
            return {"ok": True}

        def execute_sync(self, name, **kwargs):
            self.called.append((name, kwargs))
            return {"ok": True}

    registry = DummyRegistry()
    engine = ToolLoopEngine(adapter=adapter, registry=registry, max_tool_loops=5)
    messages = [{"role": "user", "content": "hi"}]

    result = await engine.arun(messages, tools=[{"type": "function", "function": {"name": "filesystem"}}])
    assert result.text == "Final answer"
    assert registry.called == [("filesystem", {"operation": "list", "path": "/tmp"})]


@pytest.mark.asyncio
async def test_native_tool_loop_chat():
    cfg = LLMGatewayConfig(llm_model_name="gpt-4o", llm_api_key="test")
    client = LLMClient(cfg)

    adapter = FakeAdapter()
    client.adapter = adapter
    client.engine.adapter = adapter

    class DummyRegistry:
        def __init__(self):
            self.called = []

        async def execute(self, name, **kwargs):
            self.called.append((name, kwargs))
            return {"ok": True}

        def execute_sync(self, name, **kwargs):
            self.called.append((name, kwargs))
            return {"ok": True}

    registry = DummyRegistry()
    client.engine.registry = registry

    messages = [{"role": "user", "content": "hi"}]
    result = await client.agenerate(messages, tools=[{"type": "function", "function": {"name": "filesystem"}}])

    assert result == "Final answer"
    assert registry.called == [("filesystem", {"operation": "list", "path": "/tmp"})]
    assert any(m.get("role") == "tool" for m in messages)


@pytest.mark.asyncio
async def test_native_tool_loop_responses():
    cfg = LLMGatewayConfig(
        llm_model_name="gpt-5.2",
        llm_api_key="test",
        llm_api_mode="responses",
    )
    client = LLMClient(cfg)

    adapter = FakeAdapter()
    client.adapter = adapter
    client.engine.adapter = adapter

    class DummyRegistry:
        def __init__(self):
            self.called = []

        async def execute(self, name, **kwargs):
            self.called.append((name, kwargs))
            return {"ok": True}

        def execute_sync(self, name, **kwargs):
            self.called.append((name, kwargs))
            return {"ok": True}

    registry = DummyRegistry()
    client.engine.registry = registry

    messages = [{"role": "user", "content": "hi"}]
    result = await client.agenerate(messages, tools=[{"type": "function", "function": {"name": "filesystem"}}])

    assert result == "Final answer"
    assert registry.called == [("filesystem", {"operation": "list", "path": "/tmp"})]
    assert any(m.get("role") == "tool" for m in messages)


@pytest.mark.asyncio
async def test_tool_calls_route_through_registry():
    cfg = LLMGatewayConfig(llm_model_name="gpt-4o", llm_api_key="test")
    client = LLMClient(cfg)

    adapter = FakeAdapter()
    client.adapter = adapter
    client.engine.adapter = adapter

    class DummyRegistry:
        def __init__(self):
            self.called = []

        async def execute(self, name, **kwargs):
            self.called.append((name, kwargs))
            return {"ok": True}

        def execute_sync(self, name, **kwargs):
            self.called.append((name, kwargs))
            return {"ok": True}

    registry = DummyRegistry()
    client.engine.registry = registry

    messages = [{"role": "user", "content": "hi"}]
    result = await client.agenerate(messages, tools=[{"type": "function", "function": {"name": "filesystem"}}])

    assert result == "Final answer"
    assert registry.called == [("filesystem", {"operation": "list", "path": "/tmp"})]
