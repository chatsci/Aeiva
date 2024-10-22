from typing import List, Dict, Optional, Any
from datetime import datetime

class Signal:
    """
    Represents an atomic unit of perception that carries raw data from the environment.
    This class defines a signal, its characteristics, and its dependencies on other signals.
    """

    def __init__(self, 
                 data: Any,
                 name: Optional[str] = None,  # Optional name for the signal
                 modularity: Optional[str] = None,
                 type: Optional[str] = None,  # Renamed to avoid keyword conflict
                 timestamp: Optional[datetime] = None,
                 id: Optional[str] = None,  # Optional unique identifier for the signal
                 dependencies: Optional[Dict[str, Any]] = None,  # Dependencies by other signal IDs with edge attributes
                 description: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a signal with its data and other optional metadata.

        Args:
            data (Any): The raw data of the signal.
            name (Optional[str]): An optional name for the signal.
            modularity (Optional[str]): The modality of the signal (e.g., image, video, text, audio).
            type (Optional[str]): A more detailed signal type (e.g., 'text', 'document', etc.).
            timestamp (Optional[datetime]): The time when the signal was created or captured.
            id (Optional[str]): Unique identifier for the signal.
            dependencies (Optional[Dict[str, Any]]): Attributes of dependencies (e.g., relationship types).
            description (Optional[str]): Description of the signal.
            metadata (Optional[Dict[str, Any]]): Optional additional metadata for the signal.
        """
        self.data = data
        self.name = name
        self.modularity = modularity
        self.type = type
        self.timestamp = timestamp or datetime.now()
        self.id = id
        self.dependencies = dependencies or {}  # Edge attributes (could be string, embedding, etc.)
        self.description = description
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the signal into a dictionary representation.
        """
        return {
            "data": self.data,
            "name": self.name,
            "modularity": self.modularity,
            "type": self.type,
            "timestamp": self.timestamp,
            "id": self.id,
            "dependencies": self.dependencies,
            "description": self.description,
            "metadata": self.metadata
        }