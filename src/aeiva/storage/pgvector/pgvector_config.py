from dataclasses import dataclass, field
from typing import Optional
from aeiva.config.base_config import BaseConfig


@dataclass
class PGVectorConfig(BaseConfig):
    """
    Configuration for PGVector (PostgreSQL with vector extension).
    """

    dbname: str = field(
        default="postgres",
        metadata={"help": "Name of the database."}
    )
    collection_name: str = field(
        default="mem0",
        metadata={"help": "Name of the collection (table name)."}
    )
    embedding_model_dims: int = field(
        default=1536,
        metadata={"help": "Dimensions of the embedding model."}
    )
    user: Optional[str] = field(
        default=None,
        metadata={"help": "Database user."}
    )
    password: Optional[str] = field(
        default=None,
        metadata={"help": "Database password."}
    )
    host: str = field(
        default="localhost",
        metadata={"help": "Database host."}
    )
    port: int = field(
        default=5432,
        metadata={"help": "Database port."}
    )
    use_diskann: bool = field(
        default=True,
        metadata={"help": "Whether to use diskann for approximate nearest neighbors search."}
    )

    def __post_init__(self):
        super().__post_init__()
        # Validate that user and password are provided
        if not self.user or not self.password:
            raise ValueError("Both 'user' and 'password' must be provided.")