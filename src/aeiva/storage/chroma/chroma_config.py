from dataclasses import dataclass, field
from typing import Optional, Any
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
            raise ValueError("Either 'path' for local storage or both 'host' and 'port' for remote connection must be provided.")