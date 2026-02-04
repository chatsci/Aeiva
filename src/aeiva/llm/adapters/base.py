from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class AdapterResponse:
    text: str
    tool_calls: List[Any]
    response_id: Optional[str]
    usage: dict
    raw: Any


class LLMAdapter:
    def build_params(self, messages, tools=None, **kwargs):
        raise NotImplementedError

    async def execute(self, params, stream: bool):
        raise NotImplementedError

    def execute_sync(self, params):
        raise NotImplementedError

    def parse_response(self, response) -> AdapterResponse:
        raise NotImplementedError

    def parse_stream_delta(self, chunk, **kwargs):
        raise NotImplementedError
