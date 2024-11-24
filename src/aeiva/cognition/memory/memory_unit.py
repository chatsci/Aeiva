# memory_unit.py

from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict, Union
from uuid import uuid4
from datetime import datetime, timezone
import json
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
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp of the memory.")
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

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the MemoryUnit instance to a dictionary format for serialization.
        Each field is handled explicitly to ensure proper serialization.

        Returns:
            Dict[str, Any]: A dictionary representation of the MemoryUnit.
        """
        return {
            "id": self.id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),  # Convert datetime to string
            "modality": self.modality,
            "type": self.type,
            "status": self.status,
            "tags": self.tags,
            "embedding": self.embedding,
            "location": self.location,
            "source_role": self.source_role,
            "source_name": self.source_name,
            "source_id": self.source_id,
            "edges": [edge.to_dict() for edge in self.edges],  # Serialize each MemoryLink
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryUnit":
        """
        Creates a MemoryUnit instance from a dictionary.
        Each field is handled explicitly to ensure proper deserialization.

        Args:
            data (dict): A dictionary containing MemoryUnit data.

        Returns:
            MemoryUnit: The created MemoryUnit instance.
        """
        try:
            return cls(
                id=data.get('id', uuid4().hex),
                content=data.get('content', ""),
                timestamp=datetime.fromisoformat(data['timestamp']) if 'timestamp' in data else datetime.now(UTC),
                modality=data.get('modality'),
                type=data.get('type'),
                status=data.get('status'),
                tags=data.get('tags', []),
                embedding=data.get('embedding'),
                location=data.get('location'),
                source_role=data.get('source_role'),
                source_name=data.get('source_name'),
                source_id=data.get('source_id', uuid4().hex),
                edges=[MemoryLink.from_dict(edge) for edge in data.get('edges', [])],
                metadata=data.get('metadata', {})
            )
        except Exception as e:
            # logger.error(f"Error deserializing MemoryUnit from dict: {e}")
            raise e