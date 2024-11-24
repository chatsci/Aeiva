# memory_config.py

from dataclasses import dataclass, field
from typing import Optional, Any
from aeiva.config.base_config import BaseConfig
from aeiva.embedding.embedder_config import EmbedderConfig
from aeiva.cognition.memory.storage_config import StorageConfig

@dataclass
class MemoryConfig(BaseConfig):
    """
    Configuration class for the Memory system.

    Attributes:
        embedder_config (EmbedderConfig): Configuration for the embedding model.
        storage_config (StorageConfig): Configuration for the storage system.
    """

    embedder_config: EmbedderConfig = field(
        metadata={"help": "Configuration for the embedding model."}
    )
    storage_config: StorageConfig = field(
        metadata={"help": "Configuration for the storage system."}
    )

    def __post_init__(self):
        super().__post_init__()
        # Perform any necessary validation
        if not self.embedder_config:
            raise ValueError("Embedder configuration must be provided.")
        if not self.storage_config:
            raise ValueError("Storage configuration must be provided.")