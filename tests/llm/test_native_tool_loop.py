import json
import importlib
import pytest

from aeiva.llm.backend import LLMResponse
from aeiva.llm.llm_client import LLMClient
from aeiva.llm.tool_loop import ToolLoopEngine
from aeiva.cognition.brain.llm_brain import LLMBrain
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.llm.tool_types import ToolCall, ToolCallDelta


class FakeBackend:
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
                ToolCall(
                    id="call_1",
                    name="filesystem",
                    arguments=json.dumps({"operation": "list", "path": "/tmp"}),
                )
            ]
            return LLMResponse("", tool_calls, "resp_1", {}, response)

        return LLMResponse("Final answer", [], "resp_2", {}, response)

    def parse_stream_delta(self, chunk, **kwargs):
        return None, None


@pytest.mark.asyncio
async def test_tool_loop_engine_executes_tools():
    adapter = FakeBackend()

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
    engine = ToolLoopEngine(backend=adapter, registry=registry, max_tool_loops=5)
    messages = [{"role": "user", "content": "hi"}]

    result = await engine.arun(messages, tools=[{"type": "function", "function": {"name": "filesystem"}}])
    assert result.text == "Final answer"
    assert registry.called == [("filesystem", {"operation": "list", "path": "/tmp"})]


@pytest.mark.asyncio
async def test_native_tool_loop_chat():
    cfg = LLMGatewayConfig(llm_model_name="gpt-4o", llm_api_key="test")
    client = LLMClient(cfg)

    adapter = FakeBackend()
    client.backend = adapter
    client.engine.backend = adapter

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

    adapter = FakeBackend()
    client.backend = adapter
    client.engine.backend = adapter

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

    adapter = FakeBackend()
    client.backend = adapter
    client.engine.backend = adapter

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


def test_stream_tool_call_delta_dict_accumulates():
    class DummyBackend:
        def build_params(self, *args, **kwargs):
            return {}

        async def execute(self, params, stream: bool):
            return {}

        def execute_sync(self, params):
            return {}

        def parse_response(self, response):
            return LLMResponse("", [], None, {}, response)

        def parse_stream_delta(self, chunk, **kwargs):
            return None, None

    engine = ToolLoopEngine(backend=DummyBackend())
    tool_calls = []

    deltas = [
        ToolCallDelta(index=0, id="call_1", name="filesystem", arguments="{\"operation\":\"list\""),
        ToolCallDelta(index=0, arguments=",\"path\":\"/tmp\"}"),
    ]
    engine._accumulate_tool_calls(tool_calls, deltas)

    assert tool_calls[0].name == "filesystem"
    assert tool_calls[0].arguments == "{\"operation\":\"list\",\"path\":\"/tmp\"}"


def test_tool_call_fallback_from_text():
    class JsonBackend(FakeBackend):
        def parse_response(self, response):
            return LLMResponse("{\"operation\":\"list\",\"path\":\"/tmp\"}", [], "resp_1", {}, response)

    engine = ToolLoopEngine(backend=JsonBackend(), max_tool_loops=2)
    tools = [{
        "type": "function",
        "function": {
            "name": "filesystem",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["operation", "path"],
            },
        },
    }]

    result = engine.run([{"role": "user", "content": "hi"}], tools=tools)
    assert result.text == "{\"operation\":\"list\",\"path\":\"/tmp\"}"


def test_tool_result_formatting_truncates_large_payload():
    class DummyBackend:
        def build_params(self, *args, **kwargs):
            return {}

        async def execute(self, params, stream: bool):
            return {}

        def execute_sync(self, params):
            return {}

        def parse_response(self, response):
            return LLMResponse("", [], None, {}, response)

        def parse_stream_delta(self, chunk, **kwargs):
            return None, None

    engine = ToolLoopEngine(backend=DummyBackend(), tool_result_max_chars=1200)
    large_payload = {
        "success": True,
        "nodes": [{"ref": f"e{i}", "text": "x" * 120} for i in range(300)],
        "screenshot": b"x" * 4096,
    }

    text = engine._format_tool_result(large_payload)
    assert len(text) <= 1200
    parsed = json.loads(text)
    assert parsed.get("truncated") is True
    assert parsed.get("original_length", 0) > 1200


def test_tool_result_formatting_summarizes_binary_values():
    class DummyBackend:
        def build_params(self, *args, **kwargs):
            return {}

        async def execute(self, params, stream: bool):
            return {}

        def execute_sync(self, params):
            return {}

        def parse_response(self, response):
            return LLMResponse("", [], None, {}, response)

        def parse_stream_delta(self, chunk, **kwargs):
            return None, None

    engine = ToolLoopEngine(backend=DummyBackend())
    text = engine._format_tool_result({"blob": bytearray(b"x" * 32)})
    parsed = json.loads(text)
    assert parsed["blob"] == "<binary:32 bytes>"

@pytest.mark.asyncio
async def test_stream_tool_call_fallback_from_text():
    class StreamBackend(FakeBackend):
        def __init__(self):
            self.calls = 0

        def build_params(self, *args, **kwargs):
            return {}

        async def execute(self, params, stream: bool):
            self.calls += 1

            async def _gen():
                yield {"type": "response.output_text.delta", "delta": "{\"operation\":\"list\",\"path\":\"/tmp\"}"}

            return _gen()

        def parse_stream_delta(self, chunk, **kwargs):
            return chunk.get("delta"), None

        def parse_response(self, response):
            return LLMResponse("", [], "resp_1", {}, response)

    engine = ToolLoopEngine(backend=StreamBackend(), max_tool_loops=2)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "filesystem",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string"},
                        "path": {"type": "string"},
                    },
                    "required": ["operation", "path"],
                },
            },
        }
    ]

    output = []
    async for chunk in engine.astream([{"role": "user", "content": "hi"}], tools=tools, stream=True):
        output.append(chunk)

    assert output == ["{\"operation\":\"list\",\"path\":\"/tmp\"}"]


@pytest.mark.asyncio
async def test_llmbrain_uses_arun():
    class DummyClient:
        def __init__(self):
            self.called = 0

        async def arun(self, messages, tools=None, stream=False):
            self.called += 1
            class Result:
                text = "ok"
            return Result()

        async def astream(self, messages, tools=None, stream=True):
            yield "ok"

        def run(self, messages, tools=None, stream=False):
            class Result:
                text = "ok"
            return Result()

    brain = LLMBrain({"llm_gateway_config": {"llm_api_key": "test"}})
    brain.state = brain.init_state()
    brain.llm_client = DummyClient()

    chunks = []
    async for chunk in brain.think([{"role": "user", "content": "hi"}], use_async=True, stream=False):
        chunks.append(chunk)

    assert chunks == ["ok"]
    assert brain.llm_client.called == 1


@pytest.mark.asyncio
async def test_multiturn_browser_tool_accepts_argument_variants(monkeypatch):
    browser_mod = importlib.import_module("aeiva.tool.meta.browser")

    class FakeBrowserService:
        def __init__(self):
            self.calls = []

        async def execute(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "success": True,
                "target_id": kwargs.get("target_id") or "tab-1",
                "url": "https://www.google.com/travel/flights",
            }

    fake_service = FakeBrowserService()
    monkeypatch.setattr(browser_mod, "get_browser_service", lambda: fake_service)

    class VariantBackend(FakeBackend):
        def __init__(self):
            self.calls = 0

        def parse_response(self, response):
            if self.calls == 0:
                self.calls += 1
                return LLMResponse(
                    "",
                    [
                        ToolCall(
                            id="call_wait",
                            name="browser",
                            arguments=json.dumps(
                                {
                                    "operation": "wait",
                                    "targetId": "tab-1",
                                    "time_ms": 2000,
                                    "loadState": "domcontentloaded",
                                    "url_contains": "flights",
                                }
                            ),
                        )
                    ],
                    "resp_1",
                    {},
                    response,
                )
            if self.calls == 1:
                self.calls += 1
                return LLMResponse(
                    "",
                    [
                        ToolCall(
                            id="call_act",
                            name="browser",
                            arguments=json.dumps(
                                {
                                    "operation": "act",
                                    "kind": "scroll",
                                    "targetId": "tab-1",
                                    "deltaY": 600,
                                }
                            ),
                        )
                    ],
                    "resp_2",
                    {},
                    response,
                )
            return LLMResponse("Final answer", [], "resp_3", {}, response)

    class ToolRegistryProxy:
        async def execute(self, name, **kwargs):
            if name != "browser":
                return {"success": False, "error": f"unexpected tool {name}"}
            return await browser_mod.browser(**kwargs)

        def execute_sync(self, name, **kwargs):
            raise NotImplementedError

    engine = ToolLoopEngine(
        backend=VariantBackend(),
        registry=ToolRegistryProxy(),
        max_tool_loops=5,
    )
    messages = [{"role": "user", "content": "help me find cheapest flight"}]
    result = await engine.arun(
        messages,
        tools=[{"type": "function", "function": {"name": "browser"}}],
    )

    assert result.text == "Final answer"
    assert len(fake_service.calls) == 2
    wait_call = fake_service.calls[0]
    act_call = fake_service.calls[1]
    assert wait_call["operation"] == "wait"
    assert wait_call["request"]["time_ms"] == 2000
    assert wait_call["request"]["loadState"] == "domcontentloaded"
    assert wait_call["request"]["targetId"] == "tab-1"
    assert act_call["operation"] == "act"
    assert act_call["request"]["kind"] == "scroll"
    assert act_call["request"]["deltaY"] == 600
