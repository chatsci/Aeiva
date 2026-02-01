"""
AEIVA Neuron: The Code Neuron abstraction.

A neuron is the atomic unit of computation in AEIVA, following the
biological pattern of receive → process → send. This module provides
the foundational abstractions for building neuromorphic AI systems.

Quick Start:
    >>> from aeiva.neuron import BaseNeuron, Signal
    >>>
    >>> class EchoNeuron(BaseNeuron):
    ...     async def process(self, signal):
    ...         return f"Echo: {signal.data}"
    ...
    >>> neuron = EchoNeuron(name="echo")
    >>> await neuron.run_forever()

Module Structure:
    signal.py    - Signal dataclass for inter-neuron communication
    state.py     - Three-layer state model (Identity, Working, Learning)
    config.py    - Configuration with sensible defaults
    metrics.py   - Observability and health monitoring
    protocols.py - Structural typing interfaces
    base_neuron.py - BaseNeuron implementation

Design Philosophy:
    - Composition over inheritance
    - Fully async for real-world performance
    - Observable and debuggable by default
    - Minimal boilerplate, maximum flexibility
"""

from .signal import Signal
from .state import IdentityState, WorkingState, LearningState
from .config import NeuronConfig, BackpressureStrategy
from .metrics import NeuronMetrics
from .protocols import (
    Neuron,
    Receivable,
    Processable,
    Sendable,
    Lifecycle,
    Persistable,
    HealthCheckable,
)
from .base_neuron import BaseNeuron


__all__ = [
    # Core
    "Signal",
    "BaseNeuron",

    # State
    "IdentityState",
    "WorkingState",
    "LearningState",

    # Config
    "NeuronConfig",
    "BackpressureStrategy",

    # Metrics
    "NeuronMetrics",

    # Protocols
    "Neuron",
    "Receivable",
    "Processable",
    "Sendable",
    "Lifecycle",
    "Persistable",
    "HealthCheckable",
]


__version__ = "0.1.0"
