from dataclasses import dataclass, field
from typing import Optional, Any
from aeiva.config.base_config import BaseConfig


@dataclass
class QdrantConfig(BaseConfig):
    """
    Configuration for Qdrant vector database.
    """

    collection_name: str = field(
        default="mem0",
        metadata={"help": "Name of the collection."}
    )
    embedding_model_dims: int = field(
        default=1536,
        metadata={"help": "Dimensions of the embedding model."}
    )
    client: Optional[Any] = field(
        default=None,
        metadata={"help": "Existing Qdrant client instance (if any)."}
    )
    host: Optional[str] = field(
        default=None,
        metadata={"help": "Host address for Qdrant server."}
    )
    port: Optional[int] = field(
        default=None,
        metadata={"help": "Port for Qdrant server."}
    )
    path: Optional[str] = field(
        default=None,
        metadata={"help": "Path for local Qdrant database storage."}
    )
    url: Optional[str] = field(
        default=None,
        metadata={"help": "Full URL for Qdrant server."}
    )
    api_key: Optional[str] = field(
        default=None,
        metadata={"help": "API key for Qdrant server authentication."}
    )
    on_disk: bool = field(
        default=False,
        metadata={"help": "Whether to enable persistent storage on disk."}
    )

    def __post_init__(self):
        super().__post_init__()
        # Validate that connection parameters are provided
        if not self.path and not ((self.host and self.port) or (self.url and self.api_key)):
            raise ValueError("Provide 'path' for local storage, or 'host' and 'port', or 'url' and 'api_key' for remote connection.")