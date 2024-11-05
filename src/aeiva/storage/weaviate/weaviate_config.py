# weaviate_config.py

from dataclasses import dataclass, field
from typing import Optional
from aeiva.config.base_config import BaseConfig


@dataclass
class WeaviateConfig(BaseConfig):
    """
    Configuration for Weaviate vector database.
    """

    url: str = field(
        default='http://localhost:8080',
        metadata={"help": "URL of the Weaviate instance (e.g., 'http://localhost:8080')."}
    )
    api_key: Optional[str] = field(
        default=None,
        metadata={"help": "API key for Weaviate authentication (if required)."}
    )
    auth_client_secret: Optional[Dict[str, Any]] = field(
        default=None,
        metadata={"help": "Authentication client secret for Weaviate (if using OIDC)."}
    )
    timeout_config: Optional[Tuple[float, float]] = field(
        default=(2, 20),
        metadata={"help": "Timeout configuration for requests (connect timeout, read timeout)."}
    )
    additional_headers: Optional[Dict[str, str]] = field(
        default=None,
        metadata={"help": "Additional headers to include in requests to Weaviate."}
    )
    embedding_model: Optional[str] = field(
        default=None,
        metadata={"help": "Name of the embedding model used (if required)."}
    )
    index_name: str = field(
        default='MyIndex',
        metadata={"help": "Name of the Weaviate index (class)."}
    )
    vector_dim: int = field(
        default=512,
        metadata={"help": "Dimensionality of the vectors stored in Weaviate."}
    )
    distance_metric: str = field(
        default='cosine',
        metadata={"help": "Distance metric to use (e.g., 'cosine', 'l2-squared', 'dot')."}
    )

    def __post_init__(self):
        super().__post_init__()
        if not self.url:
            raise ValueError("The 'url' parameter is required for Weaviate configuration.")