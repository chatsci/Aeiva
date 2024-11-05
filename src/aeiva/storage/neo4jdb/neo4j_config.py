from dataclasses import dataclass, field
from typing import Optional
from aeiva.config.base_config import BaseConfig  # Replace with your actual import


@dataclass
class Neo4jConfig(BaseConfig):
    """
    Configuration for Neo4j graph database.
    """

    uri: str = field(
        default="bolt://localhost:7687",
        metadata={"help": "URI for connecting to Neo4j (e.g., 'bolt://localhost:7687')."}
    )
    user: Optional[str] = field(
        default=None,
        metadata={"help": "Username for Neo4j authentication."}
    )
    password: Optional[str] = field(
        default=None,
        metadata={"help": "Password for Neo4j authentication."}
    )
    database: Optional[str] = field(
        default="neo4j",
        metadata={"help": "Neo4j database name."}
    )
    encrypted: bool = field(
        default=True,
        metadata={"help": "Whether to use encrypted connection (True or False)."}
    )

    def __post_init__(self):
        super().__post_init__()
        if not self.user or not self.password:
            raise ValueError("Both 'user' and 'password' must be provided for Neo4j authentication.")