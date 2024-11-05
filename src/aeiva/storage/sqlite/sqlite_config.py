# sqlite_config.py

from dataclasses import dataclass, field
from aeiva.config.base_config import BaseConfig


@dataclass
class SQLiteConfig(BaseConfig):
    """
    Configuration for SQLite database.
    """
    database: str = field(
        default=':memory:',
        metadata={"help": "Path to the SQLite database file. Use ':memory:' for an in-memory database."}
    )