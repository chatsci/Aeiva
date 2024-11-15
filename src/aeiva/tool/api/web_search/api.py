# tools/web_search/api.py

from typing import Dict, Any
import requests

def web_search(query: str) -> Dict[str, Any]:
    """
    Performs a web search and returns summarized results.

    Args:
        query (str): The search query string.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not query:
            return {
                "output": None,
                "error": "Search query must be provided.",
                "error_code": "MISSING_QUERY"
            }

        # Use DuckDuckGo Instant Answer API (no API key required)
        url = 'https://api.duckduckgo.com/'
        params = {
            'q': query,
            'format': 'json',
            'no_html': 1,
            'skip_disambig': 1
        }
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            return {
                "output": None,
                "error": f"Web search failed with status code: {response.status_code}",
                "error_code": "SEARCH_FAILED"
            }
        
        data = response.json()

        # Extract relevant information
        results = {
            'Abstract': data.get('Abstract', ''),
            'Answer': data.get('Answer', ''),
            'RelatedTopics': data.get('RelatedTopics', []),
            'Image': data.get('Image', ''),
            'Type': data.get('Type', '')
        }

        return {
            "output": results,
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error performing web search: {e}",
            "error_code": "WEB_SEARCH_FAILED"
        }