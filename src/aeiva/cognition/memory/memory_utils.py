# memory_utils.py

from aeiva.lmp.lmp import simple
from typing import Any

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