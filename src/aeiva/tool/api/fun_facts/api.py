# tools/fun_facts/api.py

from typing import Dict, Any
import requests
import os

def fun_facts(rapidapi_key: str = None) -> Dict[str, Any]:
    """
    Fetch fun facts using the RapidAPI service.

    Args:
        rapidapi_key (str, optional): The RapidAPI key. If not provided, it will use the key from the environment variables.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        # Use the provided API key if available, otherwise fall back to the environment variable
        api_key = rapidapi_key or os.getenv("RAPIDAPI_KEY")
        
        if not api_key:
            return {
                "output": None,
                "error": "RapidAPI key is missing.",
                "error_code": "MISSING_API_KEY"
            }
        
        url = "https://fun-facts1.p.rapidapi.com/api/fun-facts"
        headers = {
            'x-rapidapi-key': api_key,
            'x-rapidapi-host': "fun-facts1.p.rapidapi.com"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return {
                "output": response.json(),
                "error": None,
                "error_code": "SUCCESS"
            }
        else:
            return {
                "output": None,
                "error": f"Failed to fetch facts. Status code: {response.status_code}",
                "error_code": "FETCH_FAILED"
            }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error fetching fun facts: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }