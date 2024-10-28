# File: cognition/observation.py

from typing import Any, Dict, Optional
from datetime import datetime

class Observation:
    """
    Represents a processed input from the PerceptionSystem.
    """
    def __init__(self, data: Any, modality: str = 'text', timestamp: Optional[datetime] = None, metadata: Optional[Dict[str, Any]] = None):
        self.data = data  # The processed data (e.g., text)
        self.modality = modality
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'data': self.data,
            'modality': self.modality,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }