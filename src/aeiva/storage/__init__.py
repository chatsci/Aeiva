"""Storage abstractions and built-in backends."""

from aeiva.storage.database import Database
from aeiva.storage.database_factory import DatabaseConfigFactory, DatabaseFactory
from aeiva.storage.graph_database import (
    GraphDatabase,
    NodeNotFoundError,
    RelationshipNotFoundError,
    StorageError,
)
from aeiva.storage.relational_database import RelationalDatabase
from aeiva.storage.vector_database import VectorDatabase

__all__ = [
    "Database",
    "DatabaseConfigFactory",
    "DatabaseFactory",
    "GraphDatabase",
    "NodeNotFoundError",
    "RelationshipNotFoundError",
    "RelationalDatabase",
    "StorageError",
    "VectorDatabase",
]
