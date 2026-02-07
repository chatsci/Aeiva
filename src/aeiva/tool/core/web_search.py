"""
Web Search Tool: Frequently used shortcut for web search.

This is a Core (Tier 2) tool - a shortcut for a common operation.
Could be done with browser(operation="search"), but used so frequently
it deserves a dedicated tool to save tokens.
"""

from typing import Any, Dict, List
from urllib.parse import quote_plus

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
        fallback_results = _build_fallback_results(query, max_results=max_results)
        return {
            "success": True,
            "query": query,
            "results": fallback_results,
            "error": None,
            "search_url": f"https://www.google.com/search?q={quote_plus(query)}",
            "note": (
                "duckduckgo-search is not installed; returning actionable URL results."
            ),
        }
    except Exception as e:
        return {
            "success": True,
            "query": query,
            "results": _build_fallback_results(query, max_results=max_results),
            "error": None,
            "search_url": f"https://www.google.com/search?q={quote_plus(query)}",
            "note": f"duckduckgo-search failed ({e}); returning actionable URL results.",
        }


def _build_fallback_results(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    clean = (query or "").strip()
    encoded = quote_plus(clean)
    results: List[Dict[str, Any]] = [
        {
            "title": f"Google Search: {clean}",
            "url": f"https://www.google.com/search?q={encoded}",
            "source": "fallback",
            "snippet": "Open this search page in browser for live results.",
        },
        {
            "title": f"Bing Search: {clean}",
            "url": f"https://www.bing.com/search?q={encoded}",
            "source": "fallback",
            "snippet": "Alternative engine if Google blocks automation.",
        },
        {
            "title": f"DuckDuckGo Search: {clean}",
            "url": f"https://duckduckgo.com/?q={encoded}",
            "source": "fallback",
            "snippet": "Privacy-focused engine search page.",
        },
    ]

    lower = clean.lower()
    if any(token in lower for token in ("flight", "airfare", "ticket", "机票", "航班")):
        results.extend(
            [
                {
                    "title": f"Google Flights: {clean}",
                    "url": f"https://www.google.com/travel/flights?q={encoded}",
                    "source": "fallback",
                    "snippet": "Open Google Flights with query prefilled.",
                },
                {
                    "title": f"Skyscanner: {clean}",
                    "url": f"https://www.skyscanner.com/transport/flights/?q={encoded}",
                    "source": "fallback",
                    "snippet": "Open Skyscanner search page.",
                },
                {
                    "title": f"Trip.com Flights: {clean}",
                    "url": f"https://www.trip.com/flights/?locale=en-US&curr=USD&searchword={encoded}",
                    "source": "fallback",
                    "snippet": "Open Trip.com flight search.",
                },
            ]
        )

    limit = max(1, int(max_results or 10))
    return results[:limit]
