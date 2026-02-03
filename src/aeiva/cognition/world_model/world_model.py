"""
WorldModelNeuron: Neuron wrapper for world model functionality.

A simple observation-based world model that stores and queries
observations. Can be extended with more sophisticated world modeling
(knowledge graphs, vector embeddings, etc.).

Usage:
    from aeiva.cognition.world_model.world_model import WorldModelNeuron

    neuron = WorldModelNeuron(name="world_model", event_bus=bus)
    await neuron.setup()

Event Flow:
    perception.output ─┬─> WorldModelNeuron ─> world.updated
    action.result     ─┤
    world.query       ─┤
    world.observe     ─┘
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import json
import time

from aeiva.neuron import BaseNeuron, Signal, NeuronConfig
from aeiva.event.event_names import EventNames

if TYPE_CHECKING:
    from aeiva.event.event_bus import EventBus

logger = logging.getLogger(__name__)


DEFAULT_INPUT_EVENTS = [
    EventNames.PERCEPTION_OUTPUT,
    EventNames.ACTION_RESULT,
    EventNames.WORLD_QUERY,
    EventNames.WORLD_OBSERVE,
    EventNames.WORLD_CLEAR,
]


@dataclass
class Observation:
    """A single observation in the world model."""
    content: Any
    source: str = "unknown"
    category: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "source": self.source,
            "category": self.category,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Observation":
        return Observation(
            content=data.get("content"),
            source=data.get("source", "unknown"),
            category=data.get("category"),
            timestamp=data.get("timestamp", time.time()),
            confidence=data.get("confidence", 1.0),
        )


@dataclass
class WorldState:
    """Simple observation-based world state."""
    observations: List[Observation] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.observations)

    def add_observation(self, obs: Observation) -> None:
        self.observations.append(obs)

    def get_recent(self, n: int = 10) -> List[Observation]:
        return self.observations[-n:]

    def get_by_category(self, category: str) -> List[Observation]:
        return [o for o in self.observations if o.category == category]

    def search(self, keyword: str) -> List[Observation]:
        keyword_lower = keyword.lower()
        return [o for o in self.observations
                if keyword_lower in str(o.content).lower()]

    def clear(self) -> int:
        count = len(self.observations)
        self.observations.clear()
        return count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observations": [o.to_dict() for o in self.observations],
            "size": self.size,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "WorldState":
        state = WorldState()
        for obs_data in data.get("observations", []):
            state.observations.append(Observation.from_dict(obs_data))
        return state


@dataclass
class WorldModelNeuronConfig(NeuronConfig):
    """Configuration for WorldModelNeuron."""
    input_events: List[str] = field(default_factory=lambda: DEFAULT_INPUT_EVENTS.copy())
    output_event: str = EventNames.WORLD_UPDATED
    max_observations: int = 1000
    auto_categorize: bool = True


class WorldModelNeuron(BaseNeuron):
    """
    World model neuron for storing and querying observations.

    Selectively processes signals - not every signal results in
    a stored observation.
    """

    EMISSIONS = [EventNames.WORLD_UPDATED, EventNames.WORLD_QUERY_RESPONSE]
    CONFIG_CLASS = WorldModelNeuronConfig

    def __init__(
        self,
        name: str = "world_model",
        config: Dict = None,
        event_bus: "EventBus" = None,
        **kwargs
    ):
        neuron_config = self.build_config(config or {})
        super().__init__(name=name, config=neuron_config, event_bus=event_bus, **kwargs)

        self.SUBSCRIPTIONS = self.config.input_events.copy()
        self.state = WorldState()
        self.last_updated = time.time()
        self.observations_added = 0
        self.skipped = 0

    async def setup(self) -> None:
        """Initialize the world model neuron."""
        await super().setup()
        logger.info(f"{self.name} setup complete")

    async def process(self, signal: Signal) -> Optional[Dict[str, Any]]:
        """Process incoming signal."""
        source = signal.source

        if EventNames.WORLD_QUERY in source:
            return self.handle_query(signal)

        if EventNames.WORLD_CLEAR in source:
            return self.handle_clear()

        if EventNames.WORLD_OBSERVE in source:
            return self.handle_observe(signal)

        if not self.is_relevant(signal):
            self.skipped += 1
            return None

        return self.add_observation_from_signal(signal)

    def is_relevant(self, signal: Signal) -> bool:
        """Determine if signal should be stored as observation."""
        source = signal.source
        data = signal.data

        if "perception" in source:
            return True

        if "action" in source:
            return True

        if isinstance(data, dict):
            content = data.get("content") or data.get("text") or data.get("observation")
            if content and len(str(content)) > 10:
                return True

        return False

    def add_observation_from_signal(self, signal: Signal) -> Dict[str, Any]:
        """Create observation from signal and add to state."""
        content = self.extract_content(signal)
        category = self.infer_category(signal) if self.config.auto_categorize else None

        obs = Observation(
            content=content,
            source=signal.source,
            category=category,
        )

        self.state.add_observation(obs)
        self.last_updated = time.time()
        self.observations_added += 1

        if self.state.size > self.config.max_observations:
            excess = self.state.size - self.config.max_observations
            self.state.observations = self.state.observations[excess:]

        return {
            "action": "observation_added",
            "content": content,
            "category": category,
            "state_size": self.state.size,
        }

    def extract_content(self, signal: Signal) -> Any:
        """Extract content from signal data."""
        data = signal.data

        if isinstance(data, str):
            return data

        if isinstance(data, dict):
            for key in ["content", "text", "observation", "message", "data"]:
                if key in data:
                    return data[key]

        return data

    def infer_category(self, signal: Signal) -> str:
        """Infer category from signal source."""
        source = signal.source.lower()

        if "perception" in source:
            return "perception"
        if "action" in source:
            return "action"
        if "cognition" in source:
            return "cognition"
        if "world" in source:
            return "observation"

        return "general"

    def handle_query(self, signal: Signal) -> Dict[str, Any]:
        """Handle world state queries."""
        data = signal.data if isinstance(signal.data, dict) else {}
        query_type = data.get("type", "recent")

        if query_type == "recent":
            n = data.get("n", 10)
            observations = self.state.get_recent(n)
            return {
                "type": "recent",
                "observations": [o.to_dict() for o in observations],
                "count": len(observations),
            }

        elif query_type == "search":
            keyword = data.get("keyword", "")
            observations = self.state.search(keyword)
            return {
                "type": "search",
                "keyword": keyword,
                "observations": [o.to_dict() for o in observations],
                "count": len(observations),
            }

        elif query_type == "category":
            category = data.get("category", "")
            observations = self.state.get_by_category(category)
            return {
                "type": "category",
                "category": category,
                "observations": [o.to_dict() for o in observations],
                "count": len(observations),
            }

        elif query_type == "state":
            return {
                "type": "state",
                "size": self.state.size,
                "last_updated": self.last_updated,
            }

        else:
            return {"type": "error", "message": f"Unknown query type: {query_type}"}

    def handle_observe(self, signal: Signal) -> Dict[str, Any]:
        """Handle direct observation request."""
        data = signal.data if isinstance(signal.data, dict) else {}

        content = data.get("observation") or data.get("content")
        category = data.get("category")

        if not content:
            return {"type": "error", "message": "Missing observation content"}

        obs = Observation(
            content=content,
            source=signal.source,
            category=category,
        )

        self.state.add_observation(obs)
        self.last_updated = time.time()
        self.observations_added += 1

        return {
            "action": "observation_added",
            "content": content,
            "category": category,
            "state_size": self.state.size,
        }

    def handle_clear(self) -> Dict[str, Any]:
        """Handle clear command."""
        count = self.state.clear()
        return {
            "action": "cleared",
            "observations_removed": count,
        }

    async def send(self, output: Any, parent: Signal = None) -> None:
        """Send world model event."""
        if output is None:
            return

        signal = parent.child(self.name, output) if parent else Signal(source=self.name, data=output)
        self.working.last_output = output

        if self.events:
            emit_args = self.signal_to_event_args(self.config.output_event, signal)
            await self.events.emit(**emit_args)

    def health_check(self) -> dict:
        """Return health status."""
        health = super().health_check()
        health["state_size"] = self.state.size
        health["last_updated"] = self.last_updated
        health["observations_added"] = self.observations_added
        return health

    def serialize(self) -> str:
        """Serialize state."""
        return json.dumps(self.state.to_dict())

    def deserialize(self, data: str) -> None:
        """Deserialize state."""
        parsed = json.loads(data)
        self.state = WorldState.from_dict(parsed)
