# File: cognition/thought.py

from typing import Any, Dict, Optional
from datetime import datetime

class Thought:
    """
    Represents the output from the Brain after processing an Observation.
    """
    def __init__(self, content: Any, modality: str = 'text', timestamp: Optional[datetime] = None, metadata: Optional[Dict[str, Any]] = None):
        self.content = content  # The thought content (e.g., text)
        self.modality = modality
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.content,
            'modality': self.modality,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }