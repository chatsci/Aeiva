from aeiva.llm.adapters.litellm_adapter import LiteLLMAdapter
from aeiva.llm.adapters.base import AdapterResponse
from aeiva.llm.llm_gateway_config import LLMGatewayConfig


class DummyHandler:
    def build_params(self, messages, tools=None, **kwargs):
        return {"messages": messages, "tools": tools}

    async def execute(self, params, stream: bool = False):
        return {"ok": True}

    def execute_sync(self, params):
        return {"ok": True}

    def parse_response(self, response):
        return None, [], "hi"

    def parse_stream_delta(self, chunk, **kwargs):
        return "h", None


def test_adapter_response_contract():
    cfg = LLMGatewayConfig(llm_model_name="gpt-4o", llm_api_key="test")
    adapter = LiteLLMAdapter(cfg, handler=DummyHandler())

    dummy = {
        "id": "resp_1",
        "usage": {"prompt_tokens": 1, "completion_tokens": 2},
        "choices": [{"message": {"content": "hi"}}],
    }
    parsed = adapter.parse_response(dummy)

    assert isinstance(parsed, AdapterResponse)
    assert parsed.text == "hi"
    assert parsed.tool_calls == []
    assert parsed.response_id == "resp_1"
    assert parsed.usage["prompt_tokens"] == 1
