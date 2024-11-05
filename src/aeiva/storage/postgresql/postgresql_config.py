# postgresql_config.py

from dataclasses import dataclass, field
from aeiva.config.base_config import BaseConfig


@dataclass
class PostgreSQLConfig(BaseConfig):
    """
    Configuration for PostgreSQL database.
    """
    dbname: str = field(
        default='postgres',
        metadata={"help": "Name of the PostgreSQL database."}
    )
    user: str = field(
        default='postgres',
        metadata={"help": "Username for PostgreSQL authentication."}
    )
    password: str = field(
        default='',
        metadata={"help": "Password for PostgreSQL authentication."}
    )
    host: str = field(
        default='localhost',
        metadata={"help": "Host address for PostgreSQL server."}
    )
    port: int = field(
        default=5432,
        metadata={"help": "Port number for PostgreSQL server."}
    )