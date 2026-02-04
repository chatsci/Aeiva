"""
Web Search Tool: Frequently used shortcut for web search.

This is a Core (Tier 2) tool - a shortcut for a common operation.
Could be done with browser(operation="search"), but used so frequently
it deserves a dedicated tool to save tokens.
"""

from typing import Any, Dict, List

from ..decorator import tool
from ..capability import Capability


@tool(
    description="Search the web and return results",
    capabilities=[Capability.NETWORK],
)
async def web_search(
    query: str,
    max_results: int = 10,
) -> Dict[str, Any]:
    """
    Search the web using DuckDuckGo.

    Args:
        query: The search query.
        max_results: Maximum number of results to return.

    Returns:
        Dictionary with search results or error.
    """
    if not query:
        return {"success": False, "results": [], "error": "Query is required"}

    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        return {
            "success": True,
            "query": query,
            "results": results,
            "error": None,
        }
    except ImportError:
        return {
            "success": False,
            "results": [],
            "error": "duckduckgo-search not installed. Run: pip install duckduckgo-search",
        }
    except Exception as e:
        return {"success": False, "results": [], "error": str(e)}
