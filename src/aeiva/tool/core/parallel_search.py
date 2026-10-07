"""Optional anonymous Parallel Search MCP tool (Streamable HTTP)."""

import json
from typing import Any, Dict, List

from ..capability import Capability
from ..decorator import tool

MCP_URL = "https://search.parallel.ai/mcp"
USER_AGENT = "Aeiva/0.9 (+https://github.com/chatsci/Aeiva)"
TIMEOUT_SECONDS = 60


@tool(
    description="Search the web with free, keyless Parallel Search MCP and return source excerpts",
    capabilities=[Capability.NETWORK],
)
async def parallel_search(
    objective: str,
    search_queries: List[str],
    session_id: str = "",
) -> Dict[str, Any]:
    """Search for one objective with related keyword queries.

    Args:
        objective: Focused description of the information to find.
        search_queries: One or more related keyword queries, ideally 3-6 words each.
        session_id: Reuse the returned session_id for searches in the same conversation.

    Returns:
        Success, results with URLs and excerpts, and upstream session/usage/warnings,
        or a failure with an error message. Anonymous free-tier limits apply.
    """
    if (
        not isinstance(objective, str) or not objective.strip()
        or not isinstance(search_queries, list) or not search_queries
        or any(not isinstance(q, str) or not q.strip() for q in search_queries)
        or not isinstance(session_id, str) or len(session_id) > 100
    ):
        return {"success": False, "results": [], "error": "Provide an objective, nonempty search_queries, and a session_id of at most 100 characters"}

    # Keep discovery and existing tools usable without the optional SDK installed.
    try:
        import anyio
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError:
        return {"success": False, "results": [], "error": "Install Parallel search support with: uv sync --extra search"}

    arguments = {"objective": objective, "search_queries": search_queries}
    if session_id:
        arguments["session_id"] = session_id

    try:
        with anyio.fail_after(TIMEOUT_SECONDS):
            async with streamablehttp_client(
                MCP_URL,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT_SECONDS,
                sse_read_timeout=TIMEOUT_SECONDS,
            ) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    response = await session.call_tool("web_search", arguments)

        if response.isError:
            message = "\n".join(c.text for c in response.content if c.type == "text")
            return {"success": False, "results": [], "error": message or "Parallel Search MCP returned an error"}

        data = response.structuredContent
        if data is None:
            data = json.loads("\n".join(c.text for c in response.content if c.type == "text"))
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise ValueError("Parallel Search MCP returned an invalid search response")
        return {**data, "success": True, "error": None}
    except TimeoutError:
        return {"success": False, "results": [], "error": "Parallel Search MCP timed out"}
    except Exception as exc:
        # Cancellation (a BaseException) propagates to the caller.
        return {"success": False, "results": [], "error": str(exc)}
