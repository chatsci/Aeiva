from dataclasses import dataclass, field
from typing import Any, Optional

from aeiva.config.base_config import BaseConfig


@dataclass
class ChromaConfig(BaseConfig):
    """
    Configuration for ChromaDB vector database.
    """

    collection_name: str = field(
        default="mem0",
        metadata={"help": "Name of the collection."}
    )
    embedding_model_dims: int = field(
        default=1536,
        metadata={"help": "Embedding vector dimension metadata for compatibility."}
    )
    metric_type: str = field(
        default="COSINE",
        metadata={"help": "Distance metric metadata (e.g., COSINE, L2)."}
    )
    client: Optional[Any] = field(
        default=None,
        metadata={"help": "Existing ChromaDB client instance (if any)."}
    )
    path: Optional[str] = field(
        default=None,
        metadata={"help": "Path to the database directory for local storage."}
    )
    host: Optional[str] = field(
        default=None,
        metadata={"help": "Remote host address for ChromaDB."}
    )
    port: Optional[int] = field(
        default=None,
        metadata={"help": "Remote port for ChromaDB."}
    )

    def __post_init__(self):
        super().__post_init__()
        # Validate that either path or host and port are provided
        if not self.path and not (self.host and self.port):
            raise ValueError(
                "Either 'path' for local storage or both 'host' and 'port' "
                "for remote connection must be provided."
            )
