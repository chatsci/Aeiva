# memory_config.py

from dataclasses import dataclass, field
from typing import Optional, Any
from aeiva.config.base_config import BaseConfig
from aeiva.embedding.embedder_config import EmbedderConfig

@dataclass
class MemoryConfig(BaseConfig):
    """
    Configuration class for the Memory system.

    Attributes:
        embedder_config (EmbedderConfig): Configuration for the embedding model.
        vector_db_config (DatabaseConfig): Configuration for the vector database.
        graph_db_config (Optional[DatabaseConfig]): Configuration for the graph database.
        relational_db_config (Optional[DatabaseConfig]): Configuration for the relational database.
    """

    embedder_config: EmbedderConfig = field(
        metadata={"help": "Configuration for the embedding model."}
    )
    vector_db_provider: str = field(
        metadata={"help": "Vector database provider name."}
    )
    vector_db_config: BaseConfig = field(
        metadata={"help": "Configuration for the vector database."}
    )
    graph_db_provider: Optional[str] = field(
        default=None,
        metadata={"help": "Graph database provider name."}
    )
    graph_db_config: Optional[BaseConfig] = field(
        default=None,
        metadata={"help": "Configuration for the graph database."}
    )
    relational_db_provider: Optional[str] = field(
        default=None,
        metadata={"help": "Relational database provider name."}
    )
    relational_db_config: Optional[BaseConfig] = field(
        default=None,
        metadata={"help": "Configuration for the relational database."}
    )

    def __post_init__(self):
        super().__post_init__()
        # Perform any necessary validation
        if not self.embedder_config:
            raise ValueError("Embedder configuration must be provided.")
        if not self.vector_db_config:
            raise ValueError("Vector database configuration must be provided.")