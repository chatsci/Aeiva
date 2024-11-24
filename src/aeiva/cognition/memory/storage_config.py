# memory_config.py

from dataclasses import dataclass, field
from typing import Optional, Any
from aeiva.config.base_config import BaseConfig

@dataclass
class StorageConfig(BaseConfig):
    """
    Configuration class for the Memory storage.

    Attributes:
        vector_db_config (DatabaseConfig): Configuration for the vector database.
        graph_db_config (Optional[DatabaseConfig]): Configuration for the graph database.
        relational_db_config (Optional[DatabaseConfig]): Configuration for the relational database.
    """
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
        if not self.vector_db_config:
            raise ValueError("Vector database configuration must be provided.")