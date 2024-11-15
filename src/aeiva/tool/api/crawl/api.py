from typing import Any, Dict

import requests


def crawl(url: str) -> Dict[str, Any]:
    """
    Crawls a given website and returns its content in markdown format.

    Args:
        url (str): The website URL to crawl.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        # Validate URL
        if not url.startswith(("http://", "https://")):
            return {
                "output": None,
                "error": f"Invalid URL: {url}. URL must start with 'http://' or 'https://'.",
                "error_code": "INVALID_URL",
            }

        # Perform the crawl
        response = requests.get(url, timeout=10)

        # Check for HTTP errors
        if response.status_code != 200:
            return {
                "output": None,
                "error": f"Failed to retrieve content from URL: {url}. HTTP Status Code: {response.status_code}.",
                "error_code": "HTTP_ERROR",
            }

        # Return the content
        return {
            "output": {"content": response.text},
            "error": None,
            "error_code": "SUCCESS",
        }

    except requests.exceptions.ConnectionError as e:
        return {
            "output": None,
            "error": f"Connection error occurred: {e}",
            "error_code": "CONNECTION_ERROR",
        }

    except requests.exceptions.Timeout as e:
        return {
            "output": None,
            "error": f"Timeout error occurred: {e}",
            "error_code": "TIMEOUT_ERROR",
        }

    except Exception as e:
        return {
            "output": None,
            "error": f"An unexpected error occurred: {e}",
            "error_code": "UNEXPECTED_ERROR",
        }