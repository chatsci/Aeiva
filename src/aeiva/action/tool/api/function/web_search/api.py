# tools/web_search/api.py

import requests

def web_search(query: str) -> dict:
    """
    Perform a web search and return summarized results.

    Args:
        query (str): The search query string.

    Returns:
        dict: A dictionary containing the search results.
    """
    try:
        # Use DuckDuckGo Instant Answer API (no API key required)
        url = 'https://api.duckduckgo.com/'
        params = {
            'q': query,
            'format': 'json',
            'no_html': 1,
            'skip_disambig': 1
        }
        response = requests.get(url, params=params)
        data = response.json()

        # Extract relevant information
        results = {
            'Abstract': data.get('Abstract', ''),
            'Answer': data.get('Answer', ''),
            'RelatedTopics': data.get('RelatedTopics', []),
            'Image': data.get('Image', ''),
            'Type': data.get('Type', '')
        }
        return results
    except Exception as e:
        return {"error": f"Error performing web search: {e}"}