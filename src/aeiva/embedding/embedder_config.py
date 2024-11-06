# embedder_config.py

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class EmbedderConfig:
    """
    Configuration class for the Embedder.

    Attributes:
        provider_name (str): Name of the embedding provider (e.g., 'openai', 'cohere', 'huggingface').
        model_name (str): Name of the embedding model to use.
        api_key (Optional[str]): API key for the embedding service.
        api_base (Optional[str]): Base URL for the API endpoint.
        additional_params (Optional[Dict[str, Any]]): Additional parameters for the embedding function.
    """
    provider_name: str = field(
        default="openai",
        metadata={"help": "Name of the embedding provider (e.g., 'openai', 'cohere', 'huggingface')."}
    )
    model_name: str = field(
        default="text-embedding-ada-002",
        metadata={"help": "Name of the embedding model to use."}
    )
    api_key: Optional[str] = field(
        default=None,
        metadata={"help": "API key for the embedding service."}
    )
    api_base: Optional[str] = field(
        default=None,
        metadata={"help": "Base URL for the API endpoint."}
    )
    additional_params: Optional[Dict[str, Any]] = field(
        default_factory=dict,
        metadata={"help": "Additional parameters for the embedding function."}
    )