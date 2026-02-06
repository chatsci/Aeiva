"""Factory helpers for storage configuration and runtime backends."""

import importlib
from typing import Any, Dict, Type


def load_class(class_path: str) -> Type:
    """Load a class from a dotted import path."""
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _normalize_provider_name(provider_name: str) -> str:
    normalized = provider_name.strip().lower()
    aliases: Dict[str, str] = {
        "chromadb": "chroma",
        "kuzudb": "kuzu",
    }
    return aliases.get(normalized, normalized)


class DatabaseConfigFactory:
    """Create storage config objects by provider name."""

    provider_to_class = {
        "chroma": "aeiva.storage.chroma.chroma_config.ChromaConfig",
        "kuzu": "aeiva.storage.kuzudb.kuzudb_config.KuzuConfig",
        "sqlite": "aeiva.storage.sqlite.sqlite_config.SQLiteConfig",
    }

    @classmethod
    def create(cls, provider_name: str, **kwargs) -> Any:
        provider = _normalize_provider_name(provider_name)
        class_path = cls.provider_to_class.get(provider)
        if not class_path:
            raise ValueError(f"Unsupported database provider: {provider_name}")
        config_class = load_class(class_path)
        return config_class(**kwargs)


class DatabaseFactory:
    """Create storage runtime instances by provider name and config."""

    provider_to_class = {
        "chroma": "aeiva.storage.chroma.chroma_database.ChromaDatabase",
        "kuzu": "aeiva.storage.kuzudb.kuzudb_database.KuzuDatabase",
        "sqlite": "aeiva.storage.sqlite.sqlite_database.SQLiteDatabase",
    }

    @classmethod
    def create(cls, provider_name: str, config: Any) -> Any:
        provider = _normalize_provider_name(provider_name)
        class_path = cls.provider_to_class.get(provider)
        if not class_path:
            raise ValueError(f"Unsupported database provider: {provider_name}")

        db_class = load_class(class_path)
        if isinstance(config, dict):
            return db_class(config)
        if hasattr(config, "to_dict"):
            return db_class(config.to_dict())
        if hasattr(config, "__dict__"):
            return db_class(vars(config))
        raise TypeError("Config must be a dict or an object with to_dict()/__dict__.")
