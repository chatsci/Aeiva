# database_factory.py

import importlib
from typing import Any, Dict, Type


def load_class(class_path: str) -> Type:
    """
    Dynamically load a class from a string.

    Args:
        class_path (str): The full path to the class, e.g., 'module.submodule.ClassName'.

    Returns:
        Type: The class type.

    Raises:
        ImportError: If the module or class cannot be found.
    """
    try:
        module_path, class_name = class_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Cannot import '{class_name}' from '{module_path}': {e}")


class DatabaseConfigFactory:
    """
    Factory class to create database configuration objects based on the provider name.

    Example:
        config = DatabaseConfigFactory.create(
            'milvus',
            host='localhost',
            port=19530,
            embedding_model_dims=128,
            ...
        )
    """

    provider_to_class = {
        "milvus": "aeiva.storage.milvus.milvus_config.MilvusConfig",
        "chroma": "aeiva.storage.chroma.chroma_config.ChromaConfig",
        "azure_ai_search": "aeiva.storage.azure_ai_search.azure_ai_search_config.AzureAISearchConfig",
        "pgvector": "aeiva.storage.pgvector.pgvector_config.PGVectorConfig",
        "qdrant": "aeiva.storage.qdrant.qdrant_config.QdrantConfig",
        "neo4j": "aeiva.storage.neo4jdb.neo4j_config.Neo4jConfig",
        "sqlite": "aeiva.storage.sqlite.sqlite_config.SQLiteConfig",
        "postgresql": "aeiva.storage.postgresql.postgresql_config.PostgreSQLConfig",
        "weaviate": "aeiva.storage.weaviate.weaviate_config.WeaviateConfig",
    }

    @classmethod
    def create(cls, provider_name: str, **kwargs) -> Any:
        """
        Create a database configuration object based on the provider name.

        Args:
            provider_name (str): The name of the database provider (e.g., 'milvus', 'chroma').
            **kwargs: Configuration parameters specific to the database provider.

        Returns:
            Any: An instance of the database configuration class.

        Raises:
            ValueError: If the provider name is not supported.
            ImportError: If the configuration class cannot be imported.
        """
        class_path = cls.provider_to_class.get(provider_name.lower())
        if class_path:
            config_class = load_class(class_path)
            return config_class(**kwargs)
        else:
            raise ValueError(f"Unsupported database provider: {provider_name}")


class DatabaseFactory:
    """
    Factory class to create database objects based on the provider name and configuration.

    Example:
        db = DatabaseFactory.create('milvus', config)
    """

    provider_to_class = {
        "milvus": "aeiva.storage.milvus.milvus_database.MilvusDatabase",
        "chroma": "aeiva.storage.chroma.chroma_database.ChromaDatabase",
        "azure_ai_search": "aeiva.storage.azure_ai_search.azure_ai_search_database.AzureAISearchDatabase",
        "pgvector": "aeiva.storage.pgvector.pgvector_database.PGVectorDatabase",
        "qdrant": "aeiva.storage.qdrant.qdrant_database.QdrantDatabase",
        "neo4j": "aeiva.storage.neo4jdb.neo4j_database.Neo4jDatabase",
        "sqlite": "aeiva.storage.sqlite.sqlite_database.SQLiteDatabase",
        "postgresql": "aeiva.storage.postgresql.postgresql_database.PostgreSQLDatabase",
        "weaviate": "aeiva.storage.weaviate.weaviate_database.WeaviateDatabase",
    }

    @classmethod
    def create(cls, provider_name: str, config: Any) -> Any:
        """
        Create a database object based on the provider name and configuration.

        Args:
            provider_name (str): The name of the database provider.
            config (Any): Configuration object or dictionary for the database.

        Returns:
            Any: An instance of the database class.

        Raises:
            ValueError: If the provider name is not supported.
            ImportError: If the database class cannot be imported.
            TypeError: If the configuration cannot be converted to a dictionary.
        """
        class_path = cls.provider_to_class.get(provider_name.lower())
        if class_path:
            db_class = load_class(class_path)
            if isinstance(config, dict):
                return db_class(config)
            elif hasattr(config, 'to_dict'):
                # Assuming config is a dataclass with a 'to_dict' method
                return db_class(config.to_dict())
            elif hasattr(config, '__dict__'):
                # If config is a dataclass without 'to_dict', use __dict__
                return db_class(config.__dict__)
            else:
                raise TypeError(
                    "Config must be a dict or an object with 'to_dict' or '__dict__' method."
                )
        else:
            raise ValueError(f"Unsupported database provider: {provider_name}")