# memory_config.py

from dataclasses import dataclass, field
from typing import Optional, Any
from aeiva.config.base_config import BaseConfig
from aeiva.configs.embedder_config import EmbedderConfig
from aeiva.configs.llm_config import LLMConfig
from aeiva.storage.database_config import DatabaseConfig


@dataclass
class MemoryConfig(BaseConfig):
    """
    Configuration class for the Memory system.

    Attributes:
        embedder_config (EmbedderConfig): Configuration for the embedding model.
        vector_db_config (DatabaseConfig): Configuration for the vector database.
        graph_db_config (Optional[DatabaseConfig]): Configuration for the graph database.
        relational_db_config (Optional[DatabaseConfig]): Configuration for the relational database.
        llm_config (LLMConfig): Configuration for the language model.
    """

    embedder_config: EmbedderConfig = field(
        metadata={"help": "Configuration for the embedding model."}
    )
    vector_db_config: DatabaseConfig = field(
        metadata={"help": "Configuration for the vector database."}
    )
    graph_db_config: Optional[DatabaseConfig] = field(
        default=None,
        metadata={"help": "Configuration for the graph database."}
    )
    relational_db_config: Optional[DatabaseConfig] = field(
        default=None,
        metadata={"help": "Configuration for the relational database."}
    )
    llm_config: LLMConfig = field(
        metadata={"help": "Configuration for the language model."}
    )

    def __post_init__(self):
        super().__post_init__()
        # Perform any necessary validation
        if not self.embedder_config:
            raise ValueError("Embedder configuration must be provided.")
        if not self.vector_db_config:
            raise ValueError("Vector database configuration must be provided.")
        if not self.llm_config:
            raise ValueError("LLM configuration must be provided.")