"""
MemoryConfig: Core configuration for the memory subsystem.

Keeps memory-specific settings separate from neuron concerns.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from aeiva.config.base_config import BaseConfig


@dataclass
class MemoryConfig(BaseConfig):
    """
    Configuration for MemoryService / core memory logic.

    Attributes:
        embedder_config: Config for the embedding model (dict or BaseConfig).
        storage_config: Config for storage backends (dict or BaseConfig).
        backend_type: Backend type for non-DB storage ('memory', 'json', 'vector').
        auto_embed: Whether to embed automatically on store.
        default_retrieve_type: Default retrieval method ('similar', 'vector', 'related', 'semantic').
        default_top_k: Default top_k for retrieval.
        json_file_path: JSON path for file-backed storage.
    """

    embedder_config: Optional[Any] = None
    storage_config: Optional[Any] = None
    backend_type: str = "memory"
    auto_embed: bool = True
    default_retrieve_type: str = "similar"
    default_top_k: int = 10
    json_file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary with nested configs expanded where possible."""
        return {
            "embedder_config": self._expand(self.embedder_config),
            "storage_config": self._expand(self.storage_config),
            "backend_type": self.backend_type,
            "auto_embed": self.auto_embed,
            "default_retrieve_type": self.default_retrieve_type,
            "default_top_k": self.default_top_k,
            "json_file_path": self.json_file_path,
        }

    @staticmethod
    def _expand(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if hasattr(value, "to_dict"):
            return value.to_dict()
        if hasattr(value, "__dict__"):
            return {k: v for k, v in value.__dict__.items() if not k.startswith("_")}
        return value
