import requests
import os

def fun_facts(rapidapi_key: str = None):
    """
    Fetch fun facts using the RapidAPI service.
    Args:
        rapidapi_key (str, optional): The RapidAPI key. If not provided, it will use the key from the environment variables.
    """
    # Use the provided API key if available, otherwise fall back to the environment variable
    api_key = rapidapi_key or os.getenv("RAPIDAPI_KEY")
    
    url = "https://fun-facts1.p.rapidapi.com/api/fun-facts"
    headers = {
        'x-rapidapi-key': api_key,
        'x-rapidapi-host': "fun-facts1.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else {"error": "Failed to fetch facts"}