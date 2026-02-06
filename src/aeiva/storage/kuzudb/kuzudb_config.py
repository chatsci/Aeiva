from dataclasses import dataclass, field

from aeiva.config.base_config import BaseConfig


@dataclass
class KuzuConfig(BaseConfig):
    """Configuration for embedded Kuzu graph storage."""

    database: str = field(
        default="storage/kuzu.db",
        metadata={"help": "Path to the Kuzu database directory/file."},
    )
    read_only: bool = field(
        default=False,
        metadata={"help": "Open the Kuzu database in read-only mode."},
    )
