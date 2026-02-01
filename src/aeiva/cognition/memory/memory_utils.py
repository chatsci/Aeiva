# memory_utils.py

from aeiva.lmp.lmp import simple
from typing import Any, List, Optional

def extract_embedding_from_response(response: Any) -> Optional[List[float]]:
    """
    Extract an embedding vector from an embedder response.

    Handles both object-style (response.data[0].embedding) and
    dict-style (response["data"][0]["embedding"]) responses.

    Args:
        response: The raw response from an embedder.

    Returns:
        The embedding vector, or None if extraction fails.
    """
    if response is None:
        return None
    if hasattr(response, "data") and response.data:
        item = response.data[0]
        if isinstance(item, dict):
            return item.get("embedding")
        return getattr(item, "embedding", None)
    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("embedding")
    return None


@simple(model='gpt-4', temperature=0.7)
def extract_entities_relationships(data: Any) -> str:
    """
    You are an intelligent assistant skilled in natural language processing.
    Your task is to extract entities and the relationships between them from the provided content.
    """
    result = f"Extract entities and relationships from the following content:\n{data}"
    return result

@simple(model='gpt-4', temperature=0.7)
def derive_content(derivation_type: str, data: str) -> str:
    """
    You are a creative assistant capable of deriving new content based on specified types.
    Your task is to derive a {derivation_type} from the provided combined content.
    """
    result = f"Derive a {derivation_type} from the following content:\n{data}"
    return result