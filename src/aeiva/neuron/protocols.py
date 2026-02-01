"""
Protocols: Structural typing interfaces for neurons.

Python Protocols enable duck typing with static type checking.
Any class that implements these methods IS a Neuron, without
needing to inherit from anything.

This allows:
    - Complete flexibility in implementation
    - Easy testing with mocks
    - Clear contracts without forced inheritance

Design Philosophy:
    - Protocols define "what" not "how"
    - Use @runtime_checkable for isinstance() support
    - Keep protocols minimal - only essential methods
"""

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class Receivable(Protocol):
    """
    Something that can receive signals.

    The receive method blocks until a signal is available,
    or returns None on timeout.
    """

    async def receive(self) -> Optional[Any]:
        """Receive the next signal, or None if timed out."""
        ...


@runtime_checkable
class Processable(Protocol):
    """
    Something that can process signals.

    The process method transforms input into output.
    This is where the neuron's core logic lives.
    """

    async def process(self, signal: Any) -> Any:
        """Process a signal and produce output."""
        ...


@runtime_checkable
class Sendable(Protocol):
    """
    Something that can send signals.

    The send method emits output to downstream neurons
    via the event bus.
    """

    async def send(self, output: Any, parent: Optional[Any] = None) -> None:
        """Send output to subscribers."""
        ...


@runtime_checkable
class Neuron(Protocol):
    """
    The complete Neuron protocol: receive → process → send.

    Any class implementing these three methods IS a Neuron.
    No inheritance required.

    Example:
        >>> class MyNeuron:
        ...     name = "my_neuron"
        ...     async def receive(self): return Signal(...)
        ...     async def process(self, s): return s.data
        ...     async def send(self, o, p=None): pass
        >>> isinstance(MyNeuron(), Neuron)  # True
    """

    name: str

    async def receive(self) -> Optional[Any]:
        """Receive the next signal."""
        ...

    async def process(self, signal: Any) -> Any:
        """Process a signal and produce output."""
        ...

    async def send(self, output: Any, parent: Optional[Any] = None) -> None:
        """Send output to subscribers."""
        ...


@runtime_checkable
class Lifecycle(Protocol):
    """
    Lifecycle management protocol.

    Neurons that support proper lifecycle management implement
    setup, teardown, and graceful shutdown.
    """

    async def setup(self) -> None:
        """Initialize resources, subscribe to events."""
        ...

    async def teardown(self) -> None:
        """Release resources, unsubscribe from events."""
        ...

    async def graceful_shutdown(self, timeout: Optional[float] = None) -> None:
        """Gracefully stop, processing remaining signals."""
        ...


@runtime_checkable
class Persistable(Protocol):
    """
    State persistence protocol.

    Neurons that can save and restore their state implement
    this protocol for crash recovery and continuity.
    """

    async def save_state(self) -> None:
        """Persist current state to storage."""
        ...

    async def load_state(self) -> bool:
        """Restore state from storage. Returns True if successful."""
        ...


@runtime_checkable
class HealthCheckable(Protocol):
    """
    Health monitoring protocol.

    Neurons that support health checks implement this
    for observability and alerting.
    """

    def health_check(self) -> dict:
        """Return health status and metrics."""
        ...
