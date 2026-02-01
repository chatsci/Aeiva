"""
World model module for intelligent agent systems.

This module provides world modeling capabilities including:
- Abstract WorldModel base class
- Simple observation-based world state
- Neuron wrapper for event-based world modeling

This is a placeholder implementation. The world model stores
observations as a simple list. Future versions could use:
- Knowledge graphs for entity relationships
- Vector embeddings for semantic queries
- Predictive models for forecasting

Example usage:
    from aeiva.cognition.world_model import WorldModelNeuron

    neuron = WorldModelNeuron(name="world_model", event_bus=bus)
    await neuron.setup()

    # The neuron will react to events like:
    # - perception.output (sensory observations)
    # - action.result (action outcomes)
    # - world.query (state queries)
    # - world.observe (direct observations)
"""

# Abstract base
from aeiva.cognition.world_model.base_world_model import WorldModel

# Neuron wrapper
from aeiva.cognition.world_model.world_model import (
    WorldModelNeuron,
    WorldModelNeuronConfig,
    WorldState,
    Observation,
)

__all__ = [
    # Abstract base
    "WorldModel",

    # Neuron
    "WorldModelNeuron",
    "WorldModelNeuronConfig",

    # State classes
    "WorldState",
    "Observation",
]
