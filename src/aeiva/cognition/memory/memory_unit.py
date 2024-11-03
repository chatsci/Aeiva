from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict, Union
from uuid import uuid4
from datetime import datetime
from aeiva.cognition.memory.memory_link import MemoryLink

class MemoryUnit(BaseModel):
    """
    MemoryUnit represents a single unit of memory with core content and rich metadata.
    It includes fields for tracking information about the memory’s source, modality,
    temporal and spatial attributes, and its connections to other memory units.

    Essential Fields:
        id (str): Unique identifier for the memory unit, generated as a UUID string by default.
        content (Any): Core content of the memory, which is convertible to a string.

    Metadata:
        timestamp (datetime): Creation timestamp, defaulting to the current time.
        modality (Optional[str]): Modality type, such as 'text', 'image', 'audio'.
        type (Optional[str]): Semantic type, such as 'dialogue', 'summary', 'document'.
        status (Optional[str]): Processing status, e.g., 'raw', 'cleaned', 'processed'.
        tags (Optional[List[str]]): Tags for categorization and filtering.
        embedding (Optional[List[float]]): Vector embedding for retrieval.
        location (Optional[Union[str, Dict]]): Spatial location data.

    Source Information:
        source_role (Optional[str]): Role of the source, e.g., 'user', 'agent'.
        source_name (Optional[str]): Descriptive name of the source.
        source_id (Optional[str]): Unique identifier for the memory source, generated as a UUID string.

    Connections:
        edges (List[MemoryLink]): List of edges connecting this memory unit to others.

    Additional Metadata:
        metadata (Optional[Dict[str, Any]]): Dictionary for extensible metadata.
    """

    # Essential Fields
    id: str = Field(default_factory=lambda: uuid4().hex, description="Unique identifier for the memory unit.")
    content: Any = Field("", description="Core content of the memory unit, convertible to a string.")

    # Metadata Fields
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp of the memory.")
    modality: Optional[str] = Field(None, description="Modality type, e.g., 'text', 'image', 'audio'.")
    type: Optional[str] = Field(None, description="Semantic type, e.g., 'dialogue', 'summary'.")
    status: Optional[str] = Field(None, description="Processing status, e.g., 'raw', 'cleaned', 'derived', 'grouped', 'structured', 'indexed'.")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags for categorization or filtering.")
    embedding: Optional[List[float]] = Field(None, description="Embedding vector for memory.")
    location: Optional[Union[str, Dict]] = Field(None, description="Location data as a string or structured dictionary.")

    # Source Information
    source_role: Optional[str] = Field(None, description="Role of the memory source, e.g., 'user', 'agent'.")
    source_name: Optional[str] = Field(None, description="Descriptive name of the source, e.g., 'User123'.")
    source_id: Optional[str] = Field(default_factory=lambda: uuid4().hex, description="Unique identifier associated with the source.")

    # Connections
    edges: List[MemoryLink] = Field(default_factory=list, description="List of edges linking this memory unit to others.")

    # Additional Metadata
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Dictionary for extensible metadata.")

    def to_dict(self) -> dict:
        """Converts the MemoryUnit instance to a dictionary format for serialization."""
        return self.dict()

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryUnit":
        """Creates a MemoryUnit instance from a dictionary."""
        return cls(**data)