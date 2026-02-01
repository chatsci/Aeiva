"""
Memory unit data structure.

MemoryUnit represents a single unit of memory with rich metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from aeiva.cognition.memory.memory_link import MemoryLink


def _generate_id() -> str:
    """Generate a unique ID."""
    return uuid4().hex


def _utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


@dataclass
class MemoryUnit:
    """
    Represents a single unit of memory with core content and rich metadata.

    Attributes:
        id: Unique identifier for the memory unit.
        content: Core content of the memory (can be any type).
        timestamp: Creation timestamp (UTC).
        modality: Type of content ('text', 'image', 'audio', etc.).
        type: Semantic type ('dialogue', 'summary', 'document', etc.).
        status: Processing status ('raw', 'cleaned', 'processed', etc.).
        tags: Tags for categorization and filtering.
        embedding: Vector embedding for similarity search.
        location: Spatial location data.
        source_role: Role of the source ('user', 'agent', etc.).
        source_name: Descriptive name of the source.
        source_id: Unique identifier for the source.
        edges: Relationships to other memory units.
        metadata: Additional extensible metadata.
    """

    # Essential fields
    content: Any
    id: str = field(default_factory=_generate_id)

    # Temporal metadata
    timestamp: datetime = field(default_factory=_utc_now)

    # Content classification
    modality: Optional[str] = None
    type: Optional[str] = None
    status: str = "raw"
    tags: List[str] = field(default_factory=list)

    # Vector representation
    embedding: Optional[List[float]] = None

    # Spatial information
    location: Optional[Union[str, Dict[str, Any]]] = None

    # Source information
    source_role: Optional[str] = None
    source_name: Optional[str] = None
    source_id: Optional[str] = field(default_factory=_generate_id)

    # Graph connections
    edges: List[MemoryLink] = field(default_factory=list)

    # Extensible metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_embedded(self) -> bool:
        """Check if this memory unit has an embedding."""
        return self.embedding is not None and len(self.embedding) > 0

    @property
    def is_processed(self) -> bool:
        """Check if this memory unit has been processed."""
        return self.status not in ("raw", None)

    @property
    def has_connections(self) -> bool:
        """Check if this memory unit has connections to other units."""
        return len(self.edges) > 0

    def add_edge(self, target_id: str, relationship: str, **kwargs) -> MemoryLink:
        """
        Add a connection to another memory unit.

        Args:
            target_id: ID of the target memory unit.
            relationship: Type of relationship.
            **kwargs: Additional metadata for the link.

        Returns:
            The created MemoryLink.
        """
        link = MemoryLink(
            source_id=self.id,
            target_id=target_id,
            relationship=relationship,
            metadata=kwargs
        )
        self.edges.append(link)
        return link

    def get_edges_by_relationship(self, relationship: str) -> List[MemoryLink]:
        """Get all edges with a specific relationship type."""
        return [e for e in self.edges if e.relationship == relationship]

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> bool:
        """Remove a tag if present. Returns True if removed."""
        if tag in self.tags:
            self.tags.remove(tag)
            return True
        return False

    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata value."""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value with optional default."""
        return self.metadata.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation.
        """
        return {
            "id": self.id,
            "content": self.content if isinstance(self.content, (str, int, float, bool, list, dict)) else str(self.content),
            "timestamp": self.timestamp.isoformat(),
            "modality": self.modality,
            "type": self.type,
            "status": self.status,
            "tags": self.tags.copy(),
            "embedding": self.embedding,
            "location": self.location,
            "source_role": self.source_role,
            "source_name": self.source_name,
            "source_id": self.source_id,
            "edges": [e.to_dict() for e in self.edges],
            "metadata": self.metadata.copy()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryUnit":
        """
        Create from dictionary.

        Args:
            data: Dictionary with memory unit data.

        Returns:
            MemoryUnit instance.
        """
        # Parse timestamp
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = _utc_now()

        # Parse edges
        edges_data = data.get("edges", [])
        edges = [
            MemoryLink.from_dict(e) if isinstance(e, dict) else e
            for e in edges_data
        ]

        return cls(
            id=data.get("id", _generate_id()),
            content=data.get("content", ""),
            timestamp=timestamp,
            modality=data.get("modality"),
            type=data.get("type"),
            status=data.get("status", "raw"),
            tags=data.get("tags", []),
            embedding=data.get("embedding"),
            location=data.get("location"),
            source_role=data.get("source_role"),
            source_name=data.get("source_name"),
            source_id=data.get("source_id"),
            edges=edges,
            metadata=data.get("metadata", {})
        )

    def __str__(self) -> str:
        """String representation."""
        content_preview = str(self.content)[:50] + "..." if len(str(self.content)) > 50 else str(self.content)
        return f"MemoryUnit(id={self.id[:8]}..., content='{content_preview}', status={self.status})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"MemoryUnit(id='{self.id}', modality={self.modality}, type={self.type}, status={self.status}, edges={len(self.edges)})"
