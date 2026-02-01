"""
Signal: The fundamental unit of communication between neurons.

A Signal carries data from one neuron to another, along with metadata
for tracing, prioritization, and debugging. Signals form the backbone
of the event-driven architecture in AEIVA.

Design Philosophy:
    - Immutable-ish: Once created, a signal should not be modified
    - Traceable: Every signal has a trace_id for debugging
    - Hierarchical: Signals can spawn child signals, forming a DAG
    - Lightweight: Minimal overhead for high-frequency communication

Example:
    >>> signal = Signal(source="perception", data={"text": "hello"})
    >>> child = signal.child(source="memory", data={"encoded": True})
    >>> print(child.parent_id)  # prints signal.trace_id
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import uuid4
import time


def generate_trace_id() -> str:
    """Generate a short, unique trace identifier."""
    return uuid4().hex[:8]


@dataclass
class Signal:
    """
    A message passed between neurons in the system.

    Attributes:
        source: Identifier of the neuron that created this signal
        data: The payload being transmitted
        timestamp: When this signal was created (unix timestamp)
        trace_id: Unique identifier for tracing this signal's journey
        parent_id: trace_id of the signal that spawned this one (if any)
        hop_count: How many neurons this signal has passed through
        priority: Higher values indicate more urgent signals
        version: Schema version for forward compatibility
    """

    source: str
    data: Any
    timestamp: float = field(default_factory=time.time)
    trace_id: str = field(default_factory=generate_trace_id)
    parent_id: Optional[str] = None
    hop_count: int = 0
    priority: int = 0
    version: int = 1

    def child(self, source: str, data: Any) -> "Signal":
        """
        Create a child signal that inherits lineage from this signal.

        The child signal maintains the trace hierarchy, allowing you to
        follow the complete path of signal propagation through the system.

        Args:
            source: The neuron creating this child signal
            data: The new payload for the child

        Returns:
            A new Signal with parent_id pointing to this signal

        Example:
            >>> parent = Signal(source="brain", data={"thought": "plan"})
            >>> child = parent.child(source="action", data={"command": "execute"})
            >>> assert child.parent_id == parent.trace_id
            >>> assert child.hop_count == parent.hop_count + 1
        """
        return Signal(
            source=source,
            data=data,
            parent_id=self.trace_id,
            hop_count=self.hop_count + 1,
            priority=self.priority,
        )

    def __repr__(self) -> str:
        data_preview = str(self.data)[:50] + "..." if len(str(self.data)) > 50 else str(self.data)
        return f"Signal(trace={self.trace_id}, source={self.source}, data={data_preview})"
