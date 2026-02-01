"""
Memory link data structure.

MemoryLink represents a relationship between two memory units.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from uuid import uuid4


def _generate_id() -> str:
    """Generate a unique ID."""
    return uuid4().hex


@dataclass
class MemoryLink:
    """
    Represents a relationship between two memory units.

    Memory links enable building knowledge graphs by connecting
    related memory units with typed relationships.

    Attributes:
        source_id: ID of the source memory unit.
        target_id: ID of the target memory unit.
        relationship: Type of relationship (e.g., 'causal', 'temporal', 'part_of').
        id: Unique identifier for this link.
        weight: Optional strength/confidence of the relationship.
        metadata: Additional metadata about the relationship.
    """

    source_id: str
    target_id: str
    relationship: str = ""
    id: str = field(default_factory=_generate_id)
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Common relationship types
    CAUSAL = "causal"
    TEMPORAL = "temporal"
    PART_OF = "part_of"
    SIMILAR_TO = "similar_to"
    DERIVED_FROM = "derived_from"
    REFERENCES = "references"
    ASSOCIATION = "association"

    @property
    def is_bidirectional(self) -> bool:
        """Check if this is a bidirectional relationship."""
        bidirectional_types = {self.SIMILAR_TO, self.ASSOCIATION}
        return self.relationship in bidirectional_types

    def reverse(self) -> "MemoryLink":
        """
        Create a reversed link (target → source).

        Returns:
            New MemoryLink with swapped source and target.
        """
        return MemoryLink(
            source_id=self.target_id,
            target_id=self.source_id,
            relationship=self.relationship,
            weight=self.weight,
            metadata=self.metadata.copy()
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation.
        """
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship,
            "weight": self.weight,
            "metadata": self.metadata.copy()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryLink":
        """
        Create from dictionary.

        Args:
            data: Dictionary with link data.

        Returns:
            MemoryLink instance.
        """
        return cls(
            id=data.get("id", _generate_id()),
            source_id=data["source_id"],
            target_id=data["target_id"],
            relationship=data.get("relationship", ""),
            weight=data.get("weight", 1.0),
            metadata=data.get("metadata", {})
        )

    def __str__(self) -> str:
        """String representation."""
        return f"{self.source_id[:8]}... --[{self.relationship}]--> {self.target_id[:8]}..."

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"MemoryLink(source={self.source_id}, target={self.target_id}, relationship='{self.relationship}')"
