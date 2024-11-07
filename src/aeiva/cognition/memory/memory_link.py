from pydantic import BaseModel, Field
from typing import Any, Optional, Dict
from uuid import uuid4

class MemoryLink(BaseModel):
    """
    MemoryLink represents a relationship between two memory units, allowing
    complex structures to be built by linking individual memory units.

    Attributes:
        id (str): Unique identifier for the edge, generated as a UUID string by default.
        source_id (str): Unique identifier of the source memory unit.
        target_id (str): Unique identifier of the target memory unit.
        relationship (str): Type of relationship between memory units, such as 'causal' or 'association'.
        metadata (Optional[Dict[str, Any]]): Additional metadata for the edge.
    """
    id: str = Field(default_factory=lambda: uuid4().hex, description="Unique identifier for the edge.")
    source_id: str = Field(..., description="Unique identifier of the source memory unit.")
    target_id: str = Field(..., description="Unique identifier of the target memory unit.")
    relationship: str = Field("", description="Type of relationship, e.g., 'causal', 'temporal'.")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata for the edge.")

    def to_dict(self) -> dict:
        """Converts the MemoryLink instance to a dictionary format for serialization."""
        return self.dict()

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryLink":
        """Creates a MemoryLink instance from a dictionary."""
        return cls(**data)