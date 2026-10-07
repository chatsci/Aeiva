"""Exercise discovery and execution using the real MCP HTTP client."""

import asyncio
import builtins
import importlib
import json
from contextlib import asynccontextmanager

import httpx
import pytest

streamablehttp_client = pytest.importorskip(
    "mcp.client.streamable_http"
).streamablehttp_client

from aeiva.tool.registry import ToolRegistry

search_module = importlib.import_module("aeiva.tool.core.parallel_search")


@pytest.fixture
def registry():
    registry = ToolRegistry()
    registry.discover()
    assert registry.get("parallel_search")
    assert registry.get("web_search")
    return registry


@pytest.fixture
def server(monkeypatch):
    requests = []
    state = {"data": {"results": [{"url": "https://example.org", "excerpts": ["Useful source text"]}], "session_id": "conversation-1"}, "error": False, "text_only": False}

    def handle(request):
        assert str(request.url) == search_module.MCP_URL
        assert request.headers["user-agent"] == search_module.USER_AGENT
        assert "authorization" not in request.headers
        if request.method == "GET":
            return httpx.Response(405)
        message = json.loads(request.content)
        requests.append(message)
        method = message["method"]
        if "id" not in message:
            return httpx.Response(202)
        if method == "initialize":
            result = {"protocolVersion": message["params"]["protocolVersion"], "capabilities": {}, "serverInfo": {"name": "fixture", "version": "1"}}
        elif method == "tools/call":
            result = {"isError": state["error"], "content": [{"type": "text", "text": json.dumps(state["data"])}]}
            if not state["text_only"]:
                result["structuredContent"] = state["data"]
        elif method == "tools/list":
            result = {"tools": [{"name": "web_search", "inputSchema": {"type": "object"}}]}
        else:
            raise AssertionError(method)
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": message["id"], "result": result})

    def factory(headers=None, timeout=None, auth=None):
        return httpx.AsyncClient(headers=headers, timeout=timeout, auth=auth, transport=httpx.MockTransport(handle))

    def transport(url, **kwargs):
        return streamablehttp_client(url, httpx_client_factory=factory, **kwargs)

    monkeypatch.setattr("mcp.client.streamable_http.streamablehttp_client", transport)
    return requests, state


@pytest.mark.asyncio
async def test_registry_search_http_and_session(registry, server, monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "must-not-be-sent")
    requests, _ = server
    result = await registry.execute("parallel_search", objective="Find a source", search_queries=["example source text"])
    assert result["success"] and result["results"][0]["excerpts"]
    await registry.execute("parallel_search", objective="Another source", search_queries=["related source text"], session_id=result["session_id"])
    calls = [r["params"] for r in requests if r["method"] == "tools/call"]
    assert calls[0] == {"name": "web_search", "arguments": {"objective": "Find a source", "search_queries": ["example source text"]}}
    assert calls[1]["arguments"]["session_id"] == "conversation-1"
    schemas = registry.get_schemas(["parallel_search"])
    assert schemas[0]["function"]["parameters"]["required"] == ["objective", "search_queries"]


@pytest.mark.asyncio
async def test_text_response_and_mcp_error(registry, server):
    _, state = server
    state["text_only"] = True
    result = await registry.execute("parallel_search", objective="Find source", search_queries=["source"])
    assert result["success"]
    state["error"] = True
    result = await registry.execute("parallel_search", objective="Find source", search_queries=["source"])
    assert not result["success"] and result["error"]


@pytest.mark.asyncio
@pytest.mark.parametrize("data", [{"unexpected": True}, {"results": "bad"}])
async def test_invalid_response(registry, server, data):
    server[1]["data"] = data
    result = await registry.execute("parallel_search", objective="Find source", search_queries=["source"])
    assert not result["success"]


@pytest.mark.asyncio
@pytest.mark.parametrize("arguments", [
    {"objective": " ", "search_queries": ["source"]},
    {"objective": "source", "search_queries": []},
    {"objective": "source", "search_queries": [None]},
    {"objective": "source", "search_queries": ["source"], "session_id": "x" * 101},
])
async def test_invalid_arguments(registry, arguments):
    result = await registry.execute("parallel_search", **arguments)
    assert not result["success"]


@pytest.mark.asyncio
async def test_missing_optional_dependency(registry, monkeypatch):
    original = builtins.__import__

    def no_mcp(name, *args, **kwargs):
        if name == "mcp":
            raise ImportError("not installed")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_mcp)
    result = await registry.execute("parallel_search", objective="Find source", search_queries=["source"])
    assert not result["success"] and "uv sync --extra search" in result["error"]


@pytest.mark.asyncio
async def test_deadline_and_cancellation(registry, monkeypatch):
    entered = asyncio.Event()
    closed = []

    @asynccontextmanager
    async def blocked(*args, **kwargs):
        try:
            entered.set()
            await asyncio.Event().wait()
            yield
        finally:
            closed.append(True)

    monkeypatch.setattr("mcp.client.streamable_http.streamablehttp_client", blocked)
    monkeypatch.setattr(search_module, "TIMEOUT_SECONDS", 0.01)
    result = await registry.execute("parallel_search", objective="Find source", search_queries=["source"])
    assert not result["success"] and "timed out" in result["error"]
    monkeypatch.setattr(search_module, "TIMEOUT_SECONDS", 60)
    entered.clear()
    task = asyncio.create_task(registry.execute("parallel_search", objective="Find source", search_queries=["source"]))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(closed) == 2
