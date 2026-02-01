"""
State: The three-layer state model for neurons.

Every neuron maintains three distinct types of state:
    - IdentityState: Who am I? (persistent, defines the neuron)
    - WorkingState: What am I doing right now? (transient, current context)
    - LearningState: How do I improve? (adaptive, tracks performance)

Design Philosophy:
    - State is bound to the neuron, not separated as in pure ECS
    - Each layer has a different lifecycle and persistence strategy
    - State should be serializable for persistence and debugging

Why bound state?
    Like biological neurons where membrane potential and synaptic weights
    are inseparable from the neuron itself, our neurons own their state.
    This makes them self-contained units of computation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict
import asyncio
import time


@dataclass
class IdentityState:
    """
    Defines what this neuron IS - its persistent identity.

    This state persists across restarts and defines the neuron's
    "personality" - its accumulated knowledge, learned patterns,
    and domain-specific data.

    Attributes:
        created_at: When this neuron was first instantiated
        version: Schema version for migration support
        data: Domain-specific persistent data (e.g., memories, weights)
    """

    created_at: float = field(default_factory=time.time)
    version: int = 1
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkingState:
    """
    Tracks what the neuron is currently doing - its working memory.

    This is ephemeral state that exists only during processing.
    It's cleared or reset between sessions.

    Attributes:
        current_input: The signal currently being processed
        last_output: The most recent output produced
        pending_requests: Futures waiting for request-response completion
    """

    current_input: Any = None
    last_output: Any = None
    pending_requests: Dict[str, asyncio.Future] = field(default_factory=dict)

    def clear(self) -> None:
        """Reset working state to initial values."""
        self.current_input = None
        self.last_output = None
        # Note: pending_requests are NOT cleared - they need to complete or timeout


@dataclass
class LearningState:
    """
    Tracks how well the neuron is performing - its adaptive metrics.

    This state enables local learning rules and self-monitoring.
    It's persisted to allow continuous improvement across sessions.

    Attributes:
        utility: How useful is this neuron? (0.0 to 1.0)
        stability: How consistent is its behavior? (0.0 to 1.0)
        activation_count: Total number of times this neuron has processed signals
        last_activation: Timestamp of most recent activation
    """

    utility: float = 0.5
    stability: float = 0.5
    activation_count: int = 0
    last_activation: float = 0.0

    def record_activation(self) -> None:
        """Record that this neuron was activated."""
        self.activation_count += 1
        self.last_activation = time.time()

    @property
    def is_active(self) -> bool:
        """Check if neuron has been recently active (within last minute)."""
        return time.time() - self.last_activation < 60.0

    @property
    def is_useful(self) -> bool:
        """Check if neuron meets minimum utility threshold."""
        return self.utility > 0.1
