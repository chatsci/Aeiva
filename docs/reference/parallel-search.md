# Parallel web search

`parallel_search` is an optional native tool that returns web sources and relevant
excerpts through [Parallel Search MCP](https://docs.parallel.ai/integrations/mcp/search-mcp).
It uses the anonymous `https://search.parallel.ai/mcp` endpoint over Streamable
HTTP. No Parallel API key or saved credentials are used. The free tier has lower
rate limits; model inference is separate.

Install the optional dependency from the repository root:

```bash
uv sync --extra search
```

Add `parallel_search` to the `action_config.tools` list in your agent configuration,
keeping any existing tool names you want to use:

```yaml
action_config:
  tools:
    - web_search
    - parallel_search
```

The existing DuckDuckGo `web_search` tool and shipped configurations are unchanged.
Like other registry tools, `parallel_search` is also discovered when the runtime
is configured to load all tools. Without the extra, calling it returns installation
instructions.

You can try the tool directly through Aeiva's registry without a model key:

```bash
uv run python - <<'PY'
import asyncio
from aeiva.tool.registry import ToolRegistry

async def main():
    registry = ToolRegistry()
    registry.discover()
    result = await registry.execute(
        "parallel_search",
        objective="Find Python's official asyncio documentation",
        search_queries=["Python asyncio official documentation"],
    )
    print(result)

asyncio.run(main())
PY
```

Provide one focused `objective` and at least one nonempty `search_queries` entry.
The response includes `success`, `results` with source URLs and excerpts, and
Parallel's `session_id`, warnings, and usage when supplied. Reuse the returned
`session_id` for subsequent searches in the same conversation. Requests send
Aeiva's User-Agent and have a 60-second overall deadline; cancellation propagates
to the caller. Failures return `success: false`, an empty `results` list, and an
`error` message. The tool performs search only.
