"""
Memory module (cognition/memory).

Canonical memory implementation for AEIVA (dataclass-based, neuron-friendly).
"""

from aeiva.cognition.memory.base_memory import Memory
from aeiva.cognition.memory.memory_unit import MemoryUnit
from aeiva.cognition.memory.memory_link import MemoryLink
from aeiva.cognition.memory.memory import MemoryNeuron, MemoryNeuronConfig
from aeiva.cognition.memory.memory_service import MemoryService

# Test-only / legacy (for production, use MemoryService)
from aeiva.cognition.memory.simple_memory import SimpleMemory
from aeiva.cognition.memory.memory_storage import MemoryStorage
from aeiva.cognition.memory.memory_config import MemoryConfig
from aeiva.cognition.memory.storage_config import StorageConfig
from aeiva.cognition.memory.backend import (
    MemoryBackend,
    InMemoryBackend,
    JsonFileBackend,
    InMemoryVectorBackend,
    JsonFileVectorBackend,
    MemoryStorageBackend,
)
from aeiva.cognition.memory.memory_cleaner import MemoryCleaner
from aeiva.cognition.memory.memory_organizer import MemoryOrganizer
from aeiva.cognition.memory.memory_utils import (
    extract_entities_relationships,
    derive_content,
    extract_embedding_from_response,
)
from aeiva.cognition.memory.raw_memory import (
    RawMemoryConfig,
    RawMemoryJournal,
    RawMemoryNeuron,
    RawMemoryNeuronConfig,
)
from aeiva.cognition.memory.summary_memory import (
    SummaryMemoryNeuron,
    SummaryMemoryNeuronConfig,
)

__all__ = [
    "Memory",
    "MemoryUnit",
    "MemoryLink",
    "MemoryNeuron",
    "MemoryNeuronConfig",
    "MemoryService",
    "SimpleMemory",
    "MemoryStorage",
    "MemoryConfig",
    "StorageConfig",
    "MemoryBackend",
    "InMemoryBackend",
    "JsonFileBackend",
    "InMemoryVectorBackend",
    "JsonFileVectorBackend",
    "MemoryStorageBackend",
    "MemoryCleaner",
    "MemoryOrganizer",
    "extract_entities_relationships",
    "derive_content",
    "extract_embedding_from_response",
    "RawMemoryConfig",
    "RawMemoryJournal",
    "RawMemoryNeuron",
    "RawMemoryNeuronConfig",
    "SummaryMemoryNeuron",
    "SummaryMemoryNeuronConfig",
]
