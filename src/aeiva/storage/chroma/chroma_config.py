from dataclasses import dataclass, field

from aeiva.config.base_config import BaseConfig


@dataclass
class ChromaConfig(BaseConfig):
    """Configuration for embedded ChromaDB vector database."""

    collection_name: str = field(
        default="mem0",
        metadata={"help": "Name of the collection."},
    )
    path: str = field(
        default="storage/chromadb",
        metadata={"help": "Path to the database directory."},
    )
    embedding_model_dims: int = field(
        default=1536,
        metadata={"help": "Embedding vector dimension metadata."},
    )
    metric_type: str = field(
        default="COSINE",
        metadata={"help": "Distance metric metadata (e.g., COSINE, L2)."},
    )
